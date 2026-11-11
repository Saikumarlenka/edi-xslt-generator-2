import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from lxml import etree

from app.services.xslt_analysis_service import parse_xml_file
from app.services.python_matrix_reader import is_lx_special_charge_filter

log = logging.getLogger(__name__)
XSL_NS = "http://www.w3.org/1999/XSL/Transform"
NS = {"xsl": XSL_NS}


class PythonXsltProposalService:
    """
    Deterministic rule-based proposal generator for EDI XSLT patcher.
    Generates safe, targeted XPath replacements:
    - If crossed out in matrix: sets enclosing xsl:if test to 'false()' or comments out.
    - If unmapped segment (e.g. C2): removes completely via 'remove_node'.
    - If multiple loops/segments exist in matrix (e.g. dynamic N9 + static N9): generates both.
    - If N103/N104 mapped in N1 party loops (SH, CN): adds them dynamically.
    - If G62 constants mapped for pickup/delivery: updates them accurately.
    - If constant / hardcoded: replaces select with literal value (e.g. "'R'").
    - If canonical path provided: maps or reuses baseline XPath.
    - Strictly obeys matrix rules without hardcoded client-specific values.
    """

    def generate_proposals(
        self, baseline_path: Path, mappings: List[Dict[str, Any]], transaction: str
    ) -> List[Dict[str, Any]]:
        tree = parse_xml_file(baseline_path)
        root = tree.getroot()
        proposals: List[Dict[str, Any]] = []

        ns0_uri = root.nsmap.get("ns0") or "http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0"
        ns_dict = {"xsl": XSL_NS, "ns0": ns0_uri}

        # ── 0. Segment-level suppression / removal based on matrix ──
        inactive_segments = set()

        # Check C2: If present in baseline, check if C2 has ANY active, non-crossed mappings in matrix
        c2_nodes = root.xpath("//*[local-name()='C2']")
        if c2_nodes:
            c2_active_mappings = [
                m2 for m2 in mappings
                if (m2.get("destination_segment") == "C2" or m2.get("destination_element", "").startswith("C2"))
                and not m2.get("is_crossed", False)
                and m2.get("mapping_rule", "").lower() not in ("not mapped by default", "not mapped", "commented out")
            ]
            if not c2_active_mappings:
                xpath = "//*[local-name()='C2']"
                proposals.append({
                    "mapping_id": "MAP-SEG-C2",
                    "action": "remove_node",
                    "target_xpath": xpath,
                    "explanation": "Segment C2 is not active in matrix; removed from XSLT",
                    "confidence": "high",
                })
                inactive_segments.add("C2")
            else:
                c2_maps = {}
                for m2 in c2_active_mappings:
                    de = m2.get("destination_element")
                    consts = m2.get("constants") or []
                    val = consts[0] if consts else ""
                    if not val:
                        q = re.findall(r"['\"]([A-Za-z0-9_-]+)['\"]", m2.get("mapping_rule", ""))
                        val = q[0] if q else ""
                    if de and val:
                        c2_maps[de] = val

                c2_children = []
                for de in sorted(c2_maps.keys()):
                    c2_children.append(f"\t\t\t\t<{de}>{c2_maps[de]}</{de}>")

                if c2_children:
                    c2_xml = f"""<ns0:C2 xmlns:ns0="{ns0_uri}">\n""" + "\n".join(c2_children) + "\n\t\t\t</ns0:C2>"
                    xpath = "//*[local-name()='C2']"
                    proposals.append({
                        "mapping_id": "MAP-SEG-C2-ACTIVE",
                        "action": "replace_node",
                        "target_xpath": xpath,
                        "expression": c2_xml,
                        "explanation": f"Set matrix constants for C2 ({', '.join(sorted(c2_maps.keys()))})",
                        "confidence": "high",
                    })

        # Segments to comment out if inactive (e.g. R3, K1, S5Loop1, L7):
        segment_pairs = [("R3", "R3"), ("K1", "K1"), ("S5Loop1", "S5"), ("L7", "L7")]
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

        # ── 0.5 Special handling for N9 segments (Dynamic loop + Static segments) ──
        active_n9 = [
            m for m in mappings
            if (m.get("destination_segment") == "N9" or m.get("destination_element", "").startswith("N9"))
            and not m.get("is_crossed", False)
        ]
        if active_n9:
            dynamic_n9 = [
                m for m in active_n9
                if "ReferenceInformation" in (m.get("source_canonical_path") or "")
                or "ReferenceInformation" in (m.get("mapping_rule") or "")
                or (not m.get("is_constant") and not m.get("constants"))
            ]
            static_n9 = [
                m for m in active_n9
                if m.get("is_constant") or m.get("constants")
                or "hardcode" in (m.get("mapping_rule") or "").lower()
            ]

            # Build dynamic N9 loop XML
            n9_components = []
            if dynamic_n9:
                qualifiers = []
                has_pass_thru_note = False
                for m2 in dynamic_n9:
                    note = (m2.get("mapping_rule", "") + " " + " ".join(m2.get("related_notes", []))).lower()
                    if "passes thru all" in note or "all reference information" in note:
                        has_pass_thru_note = True
                    for cond in m2.get("conditions", []):
                        found1 = re.findall(r"@EDICode\s*=\s*['\"]*([A-Za-z0-9]{2,4})", cond, re.I)
                        for f in found1:
                            f_upper = f.upper()
                            if f_upper not in qualifiers and f_upper not in ("YES", "NO", "XML", "EDI", "IF", "OR", "AND"):
                                qualifiers.append(f_upper)

                if qualifiers and not has_pass_thru_note:
                    q_check = " or ".join([f"@EDICode='{q}'" for q in qualifiers])
                    target_test = f"({q_check}) and @ReferenceInformation != '' "
                else:
                    target_test = "@ReferenceInformation != '' "

                dyn_xml = f"""<xsl:for-each xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:ns0="{ns0_uri}" select="Header/ReferenceList/ReferenceInformation">
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
                n9_components.append(dyn_xml)

            # Build static N9 segment(s) XML
            if static_n9:
                static_n901 = [m for m in static_n9 if m.get("destination_element") == "N901"]
                static_n902 = [m for m in static_n9 if m.get("destination_element") == "N902"]
                num_static = max(len(static_n901), len(static_n902))
                for i in range(num_static):
                    val_901 = ""
                    val_902 = ""
                    if i < len(static_n901):
                        consts = static_n901[i].get("constants") or []
                        val_901 = consts[0] if consts else ""
                        if not val_901:
                            q = re.findall(r"['\"]([A-Za-z0-9_-]+)['\"]", static_n901[i].get("mapping_rule", ""))
                            val_901 = q[0] if q else ""
                    if i < len(static_n902):
                        consts = static_n902[i].get("constants") or []
                        val_902 = consts[0] if consts else ""
                        if not val_902:
                            q = re.findall(r"['\"]([A-Za-z0-9_-]+)['\"]", static_n902[i].get("mapping_rule", ""))
                            val_902 = q[0] if q else ""

                    if val_901 or val_902:
                        stat_xml = f"""<ns0:N9 xmlns:ns0="{ns0_uri}">
				<N901>{val_901}</N901>
				<N902>{val_902}</N902>
			</ns0:N9>"""
                        n9_components.append(stat_xml)

            if n9_components:
                full_n9_xml = "\n\t\t\t".join(n9_components)
                # Find replacement target in baseline
                n9_target = None
                if root.xpath("//xsl:for-each[contains(@select, 'ReferenceInformation')]", namespaces=NS):
                    n9_target = "//xsl:for-each[contains(@select, 'ReferenceInformation')]"
                elif root.xpath("//xsl:choose[.//ns0:N9 or .//*[local-name()='N9']]", namespaces=ns_dict):
                    n9_target = "//xsl:choose[.//ns0:N9 or .//*[local-name()='N9']]"

                if n9_target:
                    proposals.append({
                        "mapping_id": "MAP-N9-FULL",
                        "action": "replace_node",
                        "target_xpath": n9_target,
                        "expression": full_n9_xml,
                        "explanation": f"Generated N9 segment(s) based on matrix ({len(n9_components)} component(s))",
                        "confidence": "high",
                    })

        # ── 0.6 Special handling for N1 Loops (SH, CN, and Party Loops with matrix constants/elements) ──
        for party_code, qual_default in [("SH", "SF"), ("CN", "ST")]:
            party_mappings = [
                m for m in mappings
                if party_code in (m.get("parent_condition") or "")
                or any(party_code in c for c in m.get("conditions", []))
            ]
            n101_map = next((m for m in party_mappings if m.get("destination_element") == "N101" and not m.get("is_crossed", False)), None)
            n103_map = next((m for m in party_mappings if m.get("destination_element") == "N103" and not m.get("is_crossed", False)), None)
            n104_map = next((m for m in party_mappings if m.get("destination_element") == "N104" and not m.get("is_crossed", False)), None)

            # Determine N101 value from matrix
            n101_val = qual_default
            if n101_map:
                consts = n101_map.get("constants") or []
                if consts:
                    n101_val = consts[0]
                else:
                    q = re.findall(r"['\"]([A-Za-z0-9_-]+)['\"]", n101_map.get("mapping_rule", ""))
                    if q:
                        n101_val = q[0]
                    elif n101_map.get("source_document_reference"):
                        clean_s = n101_map.get("source_document_reference").strip().strip("'\"")
                        if len(clean_s) <= 4:
                            n101_val = clean_s

            if n103_map or n104_map or (n101_map and n101_val != qual_default):
                n1_children = [
                    f"\t\t\t\t\t\t<N101>{n101_val}</N101>",
                    """\t\t\t\t\t\t<N102>
							<xsl:call-template name="CleanAlphaField">
								<xsl:with-param name="inputText" select="Name/@Name"/>
								<xsl:with-param name="maxLength" select="60"/>
							</xsl:call-template>
						</N102>"""
                ]

                if n103_map:
                    consts = n103_map.get("constants") or []
                    n103_val = consts[0] if consts else ""
                    if not n103_val:
                        q = re.findall(r"['\"]([A-Za-z0-9_-]+)['\"]", n103_map.get("mapping_rule", ""))
                        n103_val = q[0] if q else "ZZ"
                    n1_children.append(f"\t\t\t\t\t\t<N103>{n103_val}</N103>")

                if n104_map:
                    n104_qual = qual_default
                    rule = n104_map.get("mapping_rule", "")
                    q = re.findall(r"@EDICode\s*=\s*['\"]*([A-Za-z0-9]+)['\"]*", rule, re.I)
                    if q:
                        n104_qual = q[0]
                    n1_children.append(f"""\t\t\t\t\t\t<xsl:if test="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation'][@EDICode='{n104_qual}']/@ReferenceInformation != '' or Header/ReferenceList/ReferenceInformation[@EDICode='{n104_qual}']/@ReferenceInformation != ''">
							<N104>
								<xsl:value-of select="/*[local-name()='Invoice']/*[local-name()='Header']/*[local-name()='ReferenceList']/*[local-name()='ReferenceInformation'][@EDICode='{n104_qual}']/@ReferenceInformation | Header/ReferenceList/ReferenceInformation[@EDICode='{n104_qual}']/@ReferenceInformation"/>
							</N104>
						</xsl:if>""")

                n1_target = f"//xsl:for-each[contains(@select, \"'{party_code}'\")]/*[local-name()='N1Loop1']/*[local-name()='N1']"
                if not root.xpath(n1_target, namespaces=NS):
                    n1_target = f"//xsl:for-each[contains(@select, \"'{party_code}'\")]//ns0:N1"

                n1_body = "\n".join(n1_children)
                n1_xml = f"""<ns0:N1 xmlns:ns0="{ns0_uri}" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">\n{n1_body}\n\t\t\t\t\t</ns0:N1>"""

                proposals.append({
                    "mapping_id": f"MAP-N1-{party_code}-EXT",
                    "action": "replace_node",
                    "target_xpath": n1_target,
                    "expression": n1_xml,
                    "explanation": f"Updated N1 for {party_code} (N101={n101_val}) per matrix",
                    "confidence": "high",
                })

        # ── 0.7 Special handling for G62 segments (Pickup & Delivery) ──
        g62_mappings = [
            m for m in mappings
            if (m.get("destination_segment") == "G62" or m.get("destination_element", "").startswith("G62"))
            and not m.get("is_crossed", False)
        ]
        g6201_pickup_val = None
        g6201_deliv_val = None
        for m in g62_mappings:
            if m.get("destination_element") == "G6201":
                rule = (m.get("mapping_rule") or "").lower()
                consts = m.get("constants") or []
                v = consts[0] if consts else ""
                if not v:
                    q = re.findall(r"['\"]([A-Za-z0-9]+)['\"]", rule)
                    v = q[0] if q else ""
                if "86" in rule or "86" in v or "pickup" in rule or g6201_pickup_val is None:
                    g6201_pickup_val = v or "86"
                elif "35" in rule or "35" in v or "delivery" in rule or g6201_deliv_val is None:
                    g6201_deliv_val = v or "35"

        if g6201_pickup_val:
            proposals.append({
                "mapping_id": "MAP-G62-PICKUP",
                "action": "replace_node",
                "target_xpath": "(//*[local-name()='G62'])[1]/*[local-name()='G6201']",
                "expression": f"<G6201>{g6201_pickup_val}</G6201>",
                "explanation": f"Set G6201 to '{g6201_pickup_val}' for Pickup Date per matrix",
                "confidence": "high",
            })
        if g6201_deliv_val:
            proposals.append({
                "mapping_id": "MAP-G62-DELIV",
                "action": "replace_node",
                "target_xpath": "(//*[local-name()='G62'])[2]/*[local-name()='G6201']",
                "expression": f"<G6201>{g6201_deliv_val}</G6201>",
                "explanation": f"Set G6201 to '{g6201_deliv_val}' for Delivery Date per matrix",
                "confidence": "high",
            })

        # ── 0.8 Special handling for LXLoop1 condition (Exclude product line items) ──
        lx_filter_active = False
        for m in mappings:
            seg = (m.get("destination_segment") or "").upper()
            elem = (m.get("destination_element") or "").upper()
            parent_seg = (m.get("parent_segment") or "").upper()
            if seg in ("LX", "LXLOOP1") or elem.startswith("LX") or parent_seg in ("LX", "LXLOOP1"):
                all_text = " ".join([
                    m.get("parent_condition", ""),
                    " ".join(m.get("conditions", [])),
                    m.get("mapping_rule", ""),
                    m.get("source_document_reference", ""),
                    " ".join(m.get("related_notes", [])),
                ]).lower()
                if is_lx_special_charge_filter(all_text):
                    lx_filter_active = True
                    break

        if lx_filter_active:
            line_item_fe = root.xpath("//xsl:for-each[contains(@select, 'LineItem')]", namespaces=NS)
            if line_item_fe:
                target_xpath = "//xsl:for-each[contains(@select, 'LineItem')]"
                cur_select = line_item_fe[0].get("select") or ""
                if "SpecialChargeOrAllowanceCode" not in cur_select:
                    proposals.append({
                        "mapping_id": "MAP-LOOP-LXLOOP1-CONDITION",
                        "action": "replace_select",
                        "target_xpath": target_xpath,
                        "expression": "Detail/LineItemList/LineItem[RateAndCharges/@SpecialChargeOrAllowanceCode != '']",
                        "explanation": "Filter LineItem loop to exclude product line items (populate only when RateAndCharges/@SpecialChargeOrAllowanceCode is not empty per matrix)",
                        "confidence": "high",
                    })

        # ── 0.9 Dynamic L0 elements: L006 (Volume) and L007 (VolumeUnitQualifier) ──
        active_l006 = next((m for m in mappings if m.get("destination_element") == "L006" and not m.get("is_crossed", False)), None)
        active_l007 = next((m for m in mappings if m.get("destination_element") == "L007" and not m.get("is_crossed", False)), None)

        if active_l006 or active_l007:
            l0_nodes = root.xpath("//*[local-name()='L0']")
            if l0_nodes:
                l0_node = l0_nodes[0]
                has_l006 = bool(l0_node.xpath(".//*[local-name()='L006']"))
                has_l007 = bool(l0_node.xpath(".//*[local-name()='L007']"))

                if (active_l006 and not has_l006) or (active_l007 and not has_l007):
                    l008_if = l0_node.xpath("./xsl:if[./*[local-name()='L008']]", namespaces=NS)
                    if l008_if:
                        target_xpath = "//xsl:if[./*[local-name()='L008']]"
                        orig_l008_xml = etree.tostring(l008_if[0], encoding="utf-8").decode("utf-8").strip()
                        orig_l008_xml = re.sub(r'\s+xmlns(?::[a-zA-Z0-9_]+)?="[^"]*"', '', orig_l008_xml)

                        l0_blocks = []
                        if active_l006 and not has_l006:
                            path_6 = active_l006.get("source_canonical_path", "")
                            rel_6 = active_l006.get("loop_relative_path") or (path_6.split("LineItem/")[-1] if "LineItem/" in path_6 else "LineItemQuantityAndWeight/@Volume")
                            l0_blocks.append(f"""\t\t\t\t\t\t\t<xsl:if test="{rel_6} != ''">
								<L006>
									<xsl:value-of select="{rel_6}" />
								</L006>
							</xsl:if>""")

                        if active_l007 and not has_l007:
                            path_7 = active_l007.get("source_canonical_path", "")
                            rel_7 = active_l007.get("loop_relative_path") or (path_7.split("LineItem/")[-1] if "LineItem/" in path_7 else "LineItemQuantityAndWeight/@VolumeUnitQualifier")
                            if active_l007.get("is_constant") and active_l007.get("constants"):
                                const_val = active_l007.get("constants")[0]
                                l0_blocks.append(f"""\t\t\t\t\t\t\t<L007>{const_val}</L007>""")
                            else:
                                l0_blocks.append(f"""\t\t\t\t\t\t\t<xsl:if test="{rel_7} != ''">
								<L007>
									<xsl:value-of select="{rel_7}" />
								</L007>
							</xsl:if>""")

                        l0_blocks.append(orig_l008_xml)
                        combined_xml = "\n".join(l0_blocks)

                        proposals.append({
                            "mapping_id": "MAP-L0-VOLUME",
                            "action": "replace_node",
                            "target_xpath": target_xpath,
                            "expression": combined_xml,
                            "explanation": "Insert Volume (L006) and/or VolumeUnitQualifier (L007) into L0 segment before L008 per active matrix",
                            "confidence": "high",
                        })

        # ── 1. Element-level mapping proposals ──
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

            # If the entire segment is already commented out or removed, skip child element edits
            if dest_seg in inactive_segments or dest_elem.startswith("N9") or dest_elem.startswith("G62"):
                continue

            # Skip N103/N104 since handled specifically in party loop above
            if dest_elem in ("N103", "N104"):
                continue

            # Find matching element(s) in baseline
            nodes = root.xpath(f"//*[local-name()='{dest_elem}']")
            if not nodes:
                continue

            target_node = nodes[0]

            # ── Crossed-out / Excluded Mapping (Comment out in XSLT) ──
            if is_crossed:
                # If this element has an active, non-crossed counterpart in the matrix, do not comment out
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

            # ── Dynamic rule for L108 (SpecialChargeOrAllowanceCode) ──
            if dest_elem == "L108" and not is_crossed:
                rule_text = m.get("mapping_rule", "")
                xpath = "//xsl:if[./*[local-name()='L108']]"
                matches = root.xpath(xpath, namespaces=NS)
                if len(matches) == 1:
                    INVALID_CODE_WORDS = {
                        "else", "otherwise", "default", "none", "copy", "null", "all",
                        "all others", "any", "other", "value", "empty", "omit",
                        "not mapped", "n/a", "element", "hardcode", "hardcoded",
                        "commented out", "blank", "specialchargeorallowancecode", "rateandcharges"
                    }
                    has_table_ref = any("table" in txt.lower() for txt in ([rule_text] + m.get("related_notes", [])))

                    # Check for explicit code translations (e.g. 405 -> FUE, 400 -> MSC)
                    translations = {}
                    # 1. From transformations (already parsed from lookup tables by matrix reader)
                    for t in m.get("transformations", []):
                        m_trans = re.match(r"code_map_([A-Za-z0-9]+)_to_([A-Za-z0-9]+)", t)
                        if m_trans:
                            s_code = m_trans.group(1)
                            t_code = m_trans.group(2)
                            if s_code.lower() not in INVALID_CODE_WORDS and t_code.lower() not in INVALID_CODE_WORDS:
                                translations[s_code] = t_code

                    # 2. From rule text regex:
                    # Pattern 1: IF ... = '405' THEN (send|use|translate to)? 'FUE'
                    p1 = re.findall(
                        r"(?:when|if)\s+[A-Za-z0-9_/@]+\s*=\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*(?:then\s+(?:send\s+|use\s+)?|translate\s+to\s+)\s*['\"]([A-Za-z0-9_-]+)['\"]",
                        rule_text,
                        re.I,
                    )
                    for src_c, dst_c in p1:
                        if src_c.lower() not in INVALID_CODE_WORDS and dst_c.lower() not in INVALID_CODE_WORDS:
                            translations[src_c] = dst_c

                    # Pattern 2: translate 'X' to 'Y' or 'X' -> 'Y'
                    p2 = re.findall(
                        r"(?:translate\s+)?['\"]([A-Za-z0-9_-]+)['\"]\s*(?:translate\s+to|to|->)\s*['\"]([A-Za-z0-9_-]+)['\"]",
                        rule_text,
                        re.I,
                    )
                    for src_c, dst_c in p2:
                        if src_c.lower() not in INVALID_CODE_WORDS and dst_c.lower() not in INVALID_CODE_WORDS:
                            translations[src_c] = dst_c

                    # 3. Check for explicit omit codes in matrix rule (e.g. "IF ... = 'LHS' THEN omit", "omit LHS", "!= 'LHS'")
                    omit_codes = []
                    found_omits1 = re.findall(
                        r"(?:when|if)\s+[A-Za-z0-9_/@]+\s*=\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*then\s+omit",
                        rule_text,
                        re.I,
                    )
                    for oc in found_omits1:
                        if oc.lower() not in INVALID_CODE_WORDS:
                            omit_codes.append(oc)

                    found_omits2 = re.findall(r"(?:omit|exclude|!=)\s*['\"]([A-Za-z0-9_-]+)['\"]", rule_text, re.I)
                    for oc in found_omits2:
                        if oc.lower() not in INVALID_CODE_WORDS:
                            omit_codes.append(oc)

                    omit_codes = list(dict.fromkeys(omit_codes))
                    omit_clause = "".join([f" and RateAndCharges/@SpecialChargeOrAllowanceCode != '{oc}'" for oc in omit_codes])

                    # If matrix rule is pure omission (e.g. IF @SpecialChargeOrAllowanceCode = 'LHS' THEN omit element ELSE @SpecialChargeOrAllowanceCode)
                    # and no table is referenced, do NOT use translations
                    is_pure_omission_rule = bool(re.search(r"\bif\b.*\bthen\s+omit\b", rule_text, re.I)) and not has_table_ref and not p1 and not p2
                    if is_pure_omission_rule:
                        translations = {}

                    if translations:
                        when_blocks = []
                        for src_c, dst_c in sorted(translations.items()):
                            when_blocks.append(f"""\t\t\t\t\t\t\t\t<xsl:when test="RateAndCharges/@SpecialChargeOrAllowanceCode = '{src_c}'">
									<L108>{dst_c}</L108>
								</xsl:when>""")
                        when_xml = "\n".join(when_blocks)
                        choose_xml = f"""<xsl:choose xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
{when_xml}
								<xsl:otherwise>
									<xsl:if test="RateAndCharges/@SpecialChargeOrAllowanceCode != ''{omit_clause}">
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
                            "explanation": f"L108 matrix translation: {translations} with omissions {omit_codes}",
                            "confidence": "high",
                        })
                    else:
                        test_expr = f"RateAndCharges/@SpecialChargeOrAllowanceCode != ''{omit_clause}"
                        proposals.append({
                            "mapping_id": mapping_id,
                            "action": "replace_test",
                            "target_xpath": xpath,
                            "expression": test_expr,
                            "explanation": f"L108 test expression per matrix: {test_expr}",
                            "confidence": "high",
                        })
                    continue

            # ── Special rule for B303 (ShipmentIdentificationNumber) ──
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

            # ── Special rule for B304 (ShipmentMethodOfPayment vs Constant) ──
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

            # ── Constant / Hardcoded Mapping ──
            if is_constant or (constants and not canonical_path):
                const_val = constants[0] if constants else ""
                clean_val = str(const_val).strip().strip("'\"")

                val_ofs = target_node.xpath("./xsl:value-of", namespaces=NS)
                if val_ofs:
                    xpath = f"//*[local-name()='{dest_elem}']/xsl:value-of"
                    matches = root.xpath(xpath, namespaces=NS)
                    if len(matches) == 1:
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

            # ── Canonical Path Mapping ──
            if canonical_path and canonical_path != "position()":
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

        s_vars = re.findall(r"\$([a-z0-9_]+)", s_clean)
        c_attrs = re.findall(r"@([a-z0-9_]+)", c_clean)
        if c_attrs and s_vars and c_attrs[-1] == s_vars[-1]:
            return True

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
