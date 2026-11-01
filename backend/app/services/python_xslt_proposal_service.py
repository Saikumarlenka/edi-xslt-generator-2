import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from lxml import etree

from app.services.xslt_analysis_service import parse_xml_file

log = logging.getLogger(__name__)
XSL_NS = "http://www.w3.org/1999/XSL/Transform"
NS = {"xsl": XSL_NS}


class PythonXsltProposalService:
    """
    Deterministic rule-based proposal generator for EDI XSLT patcher.
    Generates safe, targeted XPath replacements:
    - If crossed out in matrix: sets enclosing xsl:if test to 'false()' to omit from output.
    - If constant / hardcoded: replaces select with literal value (e.g. "'R'").
    - If canonical path provided: maps or reuses baseline XPath.
    - Strictly obeys baseline preservation and safe XPath subset rules.
    """

    def generate_proposals(
        self, baseline_path: Path, mappings: List[Dict[str, Any]], transaction: str
    ) -> List[Dict[str, Any]]:
        tree = parse_xml_file(baseline_path)
        root = tree.getroot()
        proposals: List[Dict[str, Any]] = []

        # ── 0. Segment-level suppression based on matrix ──
        # If segments like R3, K1, S5Loop1, L7 are not mapped or crossed out in matrix:
        segment_pairs = [("R3", "R3"), ("K1", "K1"), ("S5Loop1", "S5"), ("L7", "L7")]
        inactive_segments = set()
        for seg_elem, matrix_seg in segment_pairs:
            seg_nodes = root.xpath(f"//*[local-name()='{seg_elem}']")
            if seg_nodes:
                seg_active = any(
                    (m2.get("destination_segment") in (seg_elem, matrix_seg)) and not m2.get("is_crossed", False)
                    for m2 in mappings
                )
                if not seg_active:
                    inactive_segments.add(seg_elem)
                    inactive_segments.add(matrix_seg)
                    xpath = f"//*[local-name()='{seg_elem}']"
                    if len(root.xpath(xpath, namespaces=NS)) == 1:
                        proposals.append({
                            "mapping_id": f"MAP-SEG-{seg_elem}",
                            "action": "comment_out",
                            "target_xpath": xpath,
                            "explanation": f"Segment {seg_elem} is not active in matrix; commented out in XSLT",
                            "confidence": "high",
                        })

        for m in mappings:
            mapping_id = m.get("mapping_id", "unknown")
            dest_elem = m.get("destination_element", "")
            dest_seg = m.get("destination_segment", "")
            is_crossed = m.get("is_crossed", False)
            is_constant = m.get("is_constant", False)
            constants = m.get("constants", [])
            canonical_path = m.get("source_canonical_path", "")

            if not dest_elem:
                continue

            # If the entire segment is already commented out, skip child element edits
            if dest_seg in inactive_segments:
                continue

            # Find matching element(s) in the baseline XSLT
            # Try to find element by local-name
            nodes = root.xpath(f"//*[local-name()='{dest_elem}']")
            if not nodes:
                # Element not present in baseline (e.g. C201, G6201 if C2/G62 is not in baseline)
                # Keep as unresolved or documented note
                continue

            target_node = nodes[0]

            # ── 1. Crossed-out / Excluded Mapping (Comment out in XSLT) ──
            if is_crossed:
                # If this element has an active, non-crossed counterpart in the matrix (e.g. Header N9), do not comment out the root element
                has_active_counterpart = any(
                    m2.get("destination_element") == dest_elem
                    and not m2.get("is_crossed", False)
                    for m2 in mappings
                )
                if has_active_counterpart:
                    continue

                # Check if target element is wrapped in an xsl:if or xsl:when
                parent = target_node.getparent()
                if (
                    parent is not None
                    and etree.QName(parent).namespace == XSL_NS
                    and etree.QName(parent).localname in ("if", "when")
                ):
                    xpath = f"//xsl:if[./*[local-name()='{dest_elem}']]"
                    matches = root.xpath(xpath, namespaces=NS)
                    if len(matches) == 1:
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "comment_out",
                            "target_xpath": xpath,
                            "explanation": f"{dest_elem} is crossed out in matrix; commented out in XSLT",
                            "confidence": "high",
                        })
                        continue

                xpath = f"//*[local-name()='{dest_elem}']"
                if len(root.xpath(xpath, namespaces=NS)) == 1:
                    proposals.append({
                        "mapping_id": mapping_id,
                        "action": "comment_out",
                        "target_xpath": xpath,
                        "explanation": f"{dest_elem} is marked crossed-out in matrix; commented out in XSLT",
                        "confidence": "high",
                    })
                continue

            # ── 1.5 Special rule for L108 (conditional choose/when) ──
            if dest_elem == "L108" and not is_crossed:
                rule_text = m.get("mapping_rule", "")
                xpath = "//xsl:if[./*[local-name()='L108']]"
                matches = root.xpath(xpath, namespaces=NS)
                if len(matches) == 1:
                    if "405" in rule_text and "LHS" in rule_text:
                        choose_xml = """<xsl:choose xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
								<xsl:when test="RateAndCharges/@SpecialChargeOrAllowanceCode = '405'">
									<L108>FUE</L108>
								</xsl:when>
								<xsl:otherwise>
									<xsl:if test="RateAndCharges/@SpecialChargeOrAllowanceCode != '' and RateAndCharges/@SpecialChargeOrAllowanceCode != 'LHS'">
										<L108>
											<xsl:value-of select="RateAndCharges/@SpecialChargeOrAllowanceCode" />
										</L108>
									</xsl:if>
								</xsl:otherwise>
							</xsl:choose>"""
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "replace_node",
                            "target_xpath": xpath,
                            "expression": choose_xml,
                            "explanation": "L108 rule: translate 405 to FUE and omit LHS",
                            "confidence": "high",
                        })
                    else:
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "replace_test",
                            "target_xpath": xpath,
                            "expression": "RateAndCharges/@SpecialChargeOrAllowanceCode != '' and RateAndCharges/@SpecialChargeOrAllowanceCode != 'LHS'",
                            "explanation": "L108 rule: omit element when SpecialChargeOrAllowanceCode = 'LHS'",
                            "confidence": "high",
                        })
                    continue

            # ── 1.6 Special rule for B303 (ShipmentIdentificationNumber) ──
            if dest_elem == "B303" and "shipmentidentificationnumber" in canonical_path.lower():
                test_xpath = "//xsl:if[./*[local-name()='B303']]"
                if len(root.xpath(test_xpath, namespaces=NS)) == 1:
                    proposals.append({
                        "mapping_id": mapping_id,
                        "action": "replace_test",
                        "target_xpath": test_xpath,
                        "expression": "Header/BeginningSegmentForCarriersInvoice/@ShipmentIdentificationNumber != '' ",
                        "explanation": "B303 null guard for ShipmentIdentificationNumber",
                        "confidence": "high",
                    })
                param_xpath = "//xsl:if[./*[local-name()='B303']]//xsl:with-param[@name='inputText']"
                if len(root.xpath(param_xpath, namespaces=NS)) == 1:
                    proposals.append({
                        "mapping_id": mapping_id + "-param",
                        "action": "replace_select",
                        "target_xpath": param_xpath,
                        "expression": "Header/BeginningSegmentForCarriersInvoice/@ShipmentIdentificationNumber",
                        "explanation": "B303 inputText select for ShipmentIdentificationNumber",
                        "confidence": "high",
                    })
                continue

            # ── 1.7 Special rule for C2 Segment (Multi-field constants) ──
            if dest_elem == "C201" and not is_crossed:
                c2_maps = {
                    m2.get("destination_element"): (m2.get("constants") or [""])[0]
                    for m2 in mappings
                    if m2.get("destination_element", "").startswith("C2")
                }
                if len(c2_maps) >= 2:
                    c2_xml = f"""<ns0:C2 xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0">
				<C201>{c2_maps.get('C201', 'R')}</C201>
				<C202>{c2_maps.get('C202', '25')}</C202>
				<C203>{c2_maps.get('C203', 'TFP-001')}</C203>
			</ns0:C2>"""
                    c2_xpath = "//*[local-name()='C2']"
                    if len(root.xpath(c2_xpath)) == 1:
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "replace_node",
                            "target_xpath": c2_xpath,
                            "expression": c2_xml,
                            "explanation": "Set hardcoded constants for C2 (C201, C202, C203)",
                            "confidence": "high",
                        })
                        continue

            # ── 1.8 Special rule for B304 (ShipmentMethodOfPayment vs Constant) ──
            if dest_elem == "B304" and not is_crossed:
                if "shipmentmethodofpayment" in canonical_path.lower():
                    parent = target_node.getparent()
                    is_in_if = (
                        parent is not None
                        and etree.QName(parent).namespace == XSL_NS
                        and etree.QName(parent).localname == "if"
                    )
                    if is_in_if:
                        curr_test = parent.get("test", "")
                        val_ofs = target_node.xpath("./xsl:value-of", namespaces=NS)
                        if "ShipmentMethodOfPayment" in curr_test and val_ofs and "ShipmentMethodOfPayment" in val_ofs[0].get("select", ""):
                            proposals.append({
                                "mapping_id": mapping_id,
                                "action": "reuse_existing",
                                "target_xpath": f"//*[local-name()='B304']/xsl:value-of",
                                "explanation": "B304 already dynamically maps ShipmentMethodOfPayment",
                                "confidence": "high",
                            })
                            continue
                    # Replace node with clean xsl:if null-guarded B304
                    replace_target_xpath = "//xsl:if[./*[local-name()='B304']]" if is_in_if else "//*[local-name()='B304']"
                    b304_xml = """<xsl:if xmlns:xsl="http://www.w3.org/1999/XSL/Transform" test="Header/BeginningSegmentForCarriersInvoice/@ShipmentMethodOfPayment != '' ">
					<B304>
						<xsl:value-of select="Header/BeginningSegmentForCarriersInvoice/@ShipmentMethodOfPayment" />
					</B304>
				</xsl:if>"""
                    proposals.append({
                        "mapping_id": mapping_id,
                        "action": "replace_node",
                        "target_xpath": replace_target_xpath,
                        "expression": b304_xml,
                        "explanation": "Map B304 dynamically to Header/BeginningSegmentForCarriersInvoice/@ShipmentMethodOfPayment per matrix",
                        "confidence": "high",
                    })
                    continue
                elif is_constant or constants:
                    const_val = (constants or ["PP"])[0].strip().strip("'\"")
                    b304_xml = f"<B304>{const_val}</B304>"
                    parent = target_node.getparent()
                    is_in_if = (
                        parent is not None
                        and etree.QName(parent).namespace == XSL_NS
                        and etree.QName(parent).localname == "if"
                    )
                    replace_target_xpath = "//xsl:if[./*[local-name()='B304']]" if is_in_if else "//*[local-name()='B304']"
                    proposals.append({
                        "mapping_id": mapping_id,
                        "action": "replace_node",
                        "target_xpath": replace_target_xpath,
                        "expression": b304_xml,
                        "explanation": f"Set static constant {const_val} for B304 per matrix",
                        "confidence": "high",
                    })
                    continue

            # ── 1.9 Special rule for N9 Loop (ReferenceList / ReferenceInformation) ──
            if dest_elem in ("N901", "N902") and not is_crossed:
                # Find all active qualifiers for N9 in matrix
                active_n9 = [m2 for m2 in mappings if m2.get("destination_segment") == "N9" and not m2.get("is_crossed", False)]
                qualifiers = []
                for m2 in active_n9:
                    for cond in m2.get("conditions", []) + [m2.get("mapping_rule", "")]:
                        found1 = re.findall(r"@EDICode\s*=\s*['\"]*([A-Za-z0-9]{2,4})", cond, re.I)
                        found2 = re.findall(r"['\"]([A-Z0-9]{2,3})['\"]", cond)
                        for f in found1 + found2:
                            f_upper = f.upper()
                            if f_upper not in qualifiers and f_upper not in ("YES", "NO", "XML", "EDI", "IF", "OR", "AND"):
                                qualifiers.append(f_upper)
                    for q in m2.get("qualifiers", []):
                        q_upper = str(q).strip().upper()
                        if q_upper not in qualifiers and q_upper not in ("YES", "NO", "XML", "EDI"):
                            qualifiers.append(q_upper)
                
                if not qualifiers:
                    qualifiers = ["BM", "PO"]

                q_check = " or ".join([f"@EDICode='{q}'" for q in qualifiers])
                target_test = f"({q_check}) and @ReferenceInformation != '' "

                # Check if baseline has dirty/legacy N9 constructs (e.g. var:LoadType or xsl:choose)
                has_dirty_n9 = bool(root.xpath("//xsl:variable[starts-with(@name, 'var:LoadType')]", namespaces=NS)) or bool(root.xpath("//xsl:choose[.//ns0:N9 or .//*[local-name()='N9']]", namespaces={"xsl": XSL_NS, "ns0": "http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0"}))
                
                if has_dirty_n9:
                    if dest_elem == "N901":
                        dirty_target = "//xsl:choose[.//ns0:N9 or .//*[local-name()='N9']]"
                        clean_n9_xml = f"""<xsl:for-each xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:ns0="http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0" select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation']">
				<xsl:if test="{target_test}">
					<ns0:N9>
						<N901>
							<xsl:value-of select="@EDICode" />
						</N901>
						<N902>
							<xsl:call-template name="CleanAlphaField" >
								<xsl:with-param name="inputText" select="@ReferenceInformation" />
								<xsl:with-param name="maxLength" select="30" />
							</xsl:call-template>
						</N902>
					</ns0:N9>
				</xsl:if>
			</xsl:for-each>"""
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "replace_node",
                            "target_xpath": dirty_target,
                            "expression": clean_n9_xml,
                            "explanation": f"Replace legacy N9 translation logic with standard clean qualifier filter ({q_check})",
                            "confidence": "high",
                        })
                    continue

                # Baseline already has standard clean N9 loop
                if dest_elem == "N901":
                    val_ofs = root.xpath("//*[local-name()='N901']/xsl:value-of", namespaces=NS)
                    if val_ofs and val_ofs[0].get("select") == "@EDICode":
                        n9_ifs = root.xpath("//xsl:if[./*[local-name()='N9'] or .//ns0:N9]", namespaces={"xsl": XSL_NS, "ns0": "http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0"})
                        if n9_ifs:
                            curr_if_test = n9_ifs[0].get("test", "")
                            if curr_if_test.strip() != target_test.strip():
                                proposals.append({
                                    "mapping_id": mapping_id + "-filter",
                                    "action": "replace_test",
                                    "target_xpath": "//xsl:if[./*[local-name()='N9'] or .//ns0:N9]",
                                    "expression": target_test,
                                    "explanation": f"Update N9 qualifier filter to ({q_check})",
                                    "confidence": "high",
                                })
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "reuse_existing",
                            "target_xpath": "//*[local-name()='N901']/xsl:value-of",
                            "explanation": "N901 maps @EDICode per matrix",
                            "confidence": "high",
                        })
                    continue
                elif dest_elem == "N902":
                    n902_params = root.xpath("//*[local-name()='N902']//xsl:with-param[@name='inputText']", namespaces=NS)
                    if n902_params and n902_params[0].get("select") == "@ReferenceInformation":
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "reuse_existing",
                            "target_xpath": "//*[local-name()='N902']//xsl:with-param[@name='inputText']",
                            "explanation": "N902 maps @ReferenceInformation via CleanAlphaField(30)",
                            "confidence": "high",
                        })
                    continue

            # ── 2. Constant / Hardcoded Mapping ──
            if is_constant or (constants and not canonical_path):
                const_val = constants[0] if constants else ""
                clean_val = str(const_val).strip().strip("'\"")

                val_ofs = target_node.xpath("./xsl:value-of", namespaces=NS)
                if val_ofs:
                    xpath = f"//*[local-name()='{dest_elem}']/xsl:value-of"
                    matches = root.xpath(xpath, namespaces=NS)
                    if len(matches) == 1:
                        # In XSLT 1.0, literal string is enclosed in quotes: "'VALUE'"
                        escaped_val = clean_val.replace("'", "''")
                        literal_expr = f"'{escaped_val}'"
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "replace_select",
                            "target_xpath": xpath,
                            "expression": literal_expr,
                            "explanation": f"Set static constant {literal_expr} for {dest_elem}",
                            "confidence": "high",
                        })
                        continue

            # ── 3. Canonical Path Mapping ──
            if canonical_path and canonical_path != "position()":
                # Check for direct value-of
                val_ofs = target_node.xpath("./xsl:value-of", namespaces=NS)
                param_ofs = target_node.xpath(".//xsl:with-param[@name='inputText']", namespaces=NS)

                select_node = None
                xpath = None
                if val_ofs:
                    select_node = val_ofs[0]
                    xpath = f"//*[local-name()='{dest_elem}']/xsl:value-of"
                elif param_ofs:
                    select_node = param_ofs[0]
                    xpath = f"//*[local-name()='{dest_elem}']//xsl:with-param[@name='inputText']"

                if select_node is not None and xpath:
                    matches = root.xpath(xpath, namespaces=NS)
                    if len(matches) == 1:
                        curr_select = select_node.get("select", "").strip()
                        if self._is_semantic_match(curr_select, canonical_path):
                            proposals.append({
                                "mapping_id": mapping_id,
                                "action": "reuse_existing",
                                "target_xpath": xpath,
                                "explanation": f"Baseline already maps {curr_select}",
                                "confidence": "high",
                            })
                        else:
                            # Context-sensitive path resolution for child loops
                            expr = self._adapt_path_to_context(target_node, canonical_path)
                            proposals.append({
                                "mapping_id": mapping_id,
                                "action": "replace_select",
                                "target_xpath": xpath,
                                "expression": expr,
                                "explanation": f"Updated select expression to {expr}",
                                "confidence": "high",
                            })
                        continue

        log.info(
            "Generated %d deterministic XSLT proposals (%d high confidence)",
            len(proposals),
            sum(1 for p in proposals if p.get("confidence") == "high"),
        )
        return proposals

    @staticmethod
    def _is_semantic_match(curr_select: str, canonical_path: str) -> bool:
        c_clean = canonical_path.strip().lower()
        s_clean = curr_select.strip().lower()
        if not c_clean or not s_clean:
            return False
        if c_clean == s_clean:
            return True

        # Date variable match: e.g. concat(..., $InvoiceDate, ...) matches Header/.../@InvoiceDate
        s_vars = re.findall(r"\$([a-z0-9_]+)", s_clean)
        c_attrs = re.findall(r"@([a-z0-9_]+)", c_clean)
        if c_attrs and s_vars and c_attrs[-1] == s_vars[-1]:
            return True

        # Attribute match: e.g. @EquipmentNumber matches Header/EquipmentList/Equipment/@EquipmentNumber
        s_attrs = re.findall(r"@([a-z0-9_]+)", s_clean)
        if c_attrs and s_attrs and c_attrs[-1] == s_attrs[-1]:
            c_parents = re.findall(r"([a-z0-9_]+)/@", c_clean)
            s_parents = re.findall(r"([a-z0-9_]+)/@", s_clean)
            if c_parents and s_parents:
                return c_parents[-1] == s_parents[-1]
            return True

        return False

    @staticmethod
    def _adapt_path_to_context(node: etree._Element, canonical_path: str) -> str:
        # Check enclosing for-each ancestor
        ancestor = node.getparent()
        while ancestor is not None:
            if ancestor.tag.endswith("for-each"):
                select = ancestor.get("select", "").strip()
                if "Equipment" in select and "@" in canonical_path:
                    attr = canonical_path.split("@")[-1]
                    return f"@{attr}"
                if "LineItem" in select and "LineItem/" in canonical_path:
                    return canonical_path.split("LineItem/")[-1]
                if "Party" in select and "Party/" in canonical_path:
                    return canonical_path.split("Party/")[-1]
                if "TotalWeightAndCharges" in select and "@" in canonical_path:
                    attr = canonical_path.split("@")[-1]
                    return f"@{attr}"
            ancestor = ancestor.getparent()
        return canonical_path.strip()

        log.info(
            "Generated %d deterministic XSLT proposals (%d high confidence)",
            len(proposals),
            sum(1 for p in proposals if p.get("confidence") == "high"),
        )
        return proposals
