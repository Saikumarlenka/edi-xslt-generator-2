import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.models.mapping import MappingRecord, MappingSpecification, ReviewPoint
from app.services.canonical_path_resolver import CanonicalPathResolver

log = logging.getLogger(__name__)

DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def is_lx_special_charge_filter(text: str) -> bool:
    """
    Detects conditions requiring LineItem / LXLoop1 to exclude product line items
    or populate only when SpecialChargeOrAllowanceCode is not empty.
    """
    if not text:
        return False
    t = text.lower()
    has_sp_charge = any(k in t for k in ("specialcharge", "special charge", "special_charge", "charge allowance", "charge or allowance"))
    has_not_empty = any(k in t for k in ("not empty", "must not be empty", "is not empty", "!= ''", '!= ""', "!= null", "<> ''", "non empty", "non-empty"))
    has_prod_filter = any(k in t for k in ("do not product", "do not include product", "exclude product", "no product line", "omit product", "without product", "dont need product", "don't need product"))
    has_populate_only = any(k in t for k in ("populate only", "only when", "only for", "needs only"))

    if (has_sp_charge and has_not_empty) or (has_sp_charge and has_populate_only) or has_prod_filter:
        return True
    return False


class PythonMatrixReaderService:
    """
    Deterministic rule-based mapping matrix reader using pure Python.
    Parses mapping matrices (DOCX, XLSX, CSV) with high fidelity:
    - High-precision noise cancellation & row blocking.
    - Captures exact Destination Segment and Destination Element.
    - Resolves Source Canonical Paths hierarchically from parent containers.
    - Identifies Conditions (both parent loop/segment conditions and element conditions).
    - Identifies Constants, Static Values, and Hardcoded literals (if no path, marked as constant).
    - Detects Strikethrough / Crossed-out elements (via XML runs and text notes).
    """

    def __init__(self):
        self._canonical_resolver = CanonicalPathResolver()

    def read_matrix(self, docx_path: Path, transaction: str) -> MappingSpecification:
        path = Path(docx_path)
        ext = path.suffix.lower()

        if ext == ".docx":
            return self._parse_docx(path, transaction)
        elif ext in (".xlsx", ".xls"):
            return self._parse_xlsx(path, transaction)
        elif ext in (".csv", ".tsv"):
            return self._parse_csv(path, transaction)
        else:
            # Fall back to attempting DOCX parse (e.g. if file has no extension)
            try:
                return self._parse_docx(path, transaction)
            except Exception as exc:
                raise ValueError(f"Unsupported matrix file format: {ext} ({exc})")

    def _parse_docx(self, docx_path: Path, transaction: str) -> MappingSpecification:
        log.info("Parsing matrix DOCX deterministically via Python: %s", docx_path)
        with zipfile.ZipFile(docx_path) as z:
            if "word/document.xml" not in z.namelist():
                raise ValueError("Invalid DOCX file: missing word/document.xml")
            doc_xml = z.read("word/document.xml")

        tree = ET.fromstring(doc_xml)
        tables = tree.findall(".//w:tbl", DOCX_NS)
        if not tables:
            raise ValueError("No tables found in the mapping matrix document.")

        # Identify candidate mapping tables and lookup/code mapping tables
        candidate_tables = []
        lookup_tables = []

        for tbl in tables:
            rows = tbl.findall("./w:tr", DOCX_NS)
            if not rows:
                continue

            # Inspect first two rows for headers
            header_cells = [self._get_cell_text(c)[0] for c in rows[0].findall("./w:tc", DOCX_NS)]
            if len(rows) > 1:
                header_cells.extend([self._get_cell_text(c)[0] for c in rows[1].findall("./w:tc", DOCX_NS)])
            header_joined = " ".join(header_cells).lower()

            if any(k in header_joined for k in ("x12", "edi", "canonical", "node name", "destination", "segment")):
                candidate_tables.append((len(rows), tbl))
            elif any(k in header_joined for k in ("rateandcharges", "referencelist", "comments", "code")):
                lookup_tables.append(tbl)

        if candidate_tables:
            # Pick the candidate table with the most rows
            main_table = max(candidate_tables, key=lambda item: item[0])[1]
            # Any remaining candidate tables with fewer rows could be lookup tables
            for row_count, tbl in candidate_tables:
                if tbl != main_table:
                    lookup_tables.append(tbl)
        else:
            # Fallback to the table with the most rows
            main_table = max(tables, key=lambda t: len(t.findall("./w:tr", DOCX_NS)))

        # Parse lookup tables for code translations (e.g. 405 -> FUE)
        lookup_translations = self._extract_lookup_translations(lookup_tables)

        # Parse the main mapping table
        mappings, review_points = self._extract_mappings_from_table(main_table, transaction, lookup_translations)

        if not mappings:
            raise ValueError("No valid EDI mapping rows could be extracted from matrix.")

        summary = (
            f"Extracted {len(mappings)} EDI {transaction} mapping rows using Python deterministic parser. "
            f"Identified {sum(1 for m in mappings if m.is_constant)} constants, "
            f"{sum(1 for m in mappings if m.is_crossed)} crossed-out/excluded elements, and "
            f"{sum(1 for m in mappings if m.conditions)} conditional elements. "
            f"Generated {len(review_points)} schema validation review points."
        )

        return MappingSpecification(
            transaction=transaction,
            document_summary=summary,
            mappings=mappings,
            extraction_method="python",
            review_points=review_points,
        )

    def _extract_mappings_from_table(
        self, tbl: ET.Element, transaction: str, lookups: Dict[str, Any]
    ) -> tuple[List[MappingRecord], List[ReviewPoint]]:
        rows = tbl.findall("./w:tr", DOCX_NS)
        mappings: List[MappingRecord] = []
        review_points: List[ReviewPoint] = []
        id_counts: Dict[str, int] = {}

        # Hierarchical context trackers
        current_section = ""
        current_parent_seg = ""
        current_parent_path = ""
        current_parent_cond = ""

        for r_idx, r in enumerate(rows):
            cells = r.findall("./w:tc", DOCX_NS)
            if not cells:
                continue

            cell_data = [self._get_cell_text(c) for c in cells]
            texts = [t for t, _ in cell_data]
            strikes = [s for _, s in cell_data]

            # ── Blocking Skill 1: Header rows & Metadata rows ──
            if r_idx < 2:
                continue
            if any("node name" in t.lower() for t in texts) or any("x12_00401" in t.lower() for t in texts):
                continue
            if not any(texts):
                continue

            # Identify columns
            # Standard matrix structure:
            # Col 0: # / row num
            # Col 1: Destination Element / Node (e.g. ST, ST01, B3, B301, C201, N901)
            # Col 2: BA Comments (optional)
            # Col 3: Canonical Node Name / Path / Value / Condition
            # Col 4: Notes / format rules
            dest_raw = texts[1].strip() if len(texts) > 1 else ""
            ba_raw = texts[2].strip() if len(texts) > 2 else ""
            source_raw = texts[3].strip() if len(texts) > 3 else ""
            notes_raw = texts[4].strip() if len(texts) > 4 else ""

            # Normalize quotes, spaces, and weird typography
            dest = self._normalize_text(dest_raw)
            ba_comment = self._normalize_text(ba_raw)
            source_val = self._normalize_text(source_raw)
            notes = self._normalize_text(notes_raw)

            # Combined notes
            combined_notes = []
            if notes:
                combined_notes.append(notes)
            if ba_comment and ba_comment.lower() not in ("not mapped", "none by default"):
                combined_notes.append(ba_comment)

            # ── Blocking Skill 2: Detect section dividers & container rows ──
            # E.g. "Header", "Summary", "Detail/LineItem", "PartyList"
            if not dest and source_val in ("Header", "Summary", "Detail/LineItem", "PartyList"):
                current_section = source_val
                if source_val == "Summary":
                    current_parent_path = "Summary"
                    current_parent_seg = ""
                    current_parent_cond = ""
                elif source_val == "Detail/LineItem":
                    current_parent_path = "Detail/LineItem"
                    current_parent_seg = "LXLoop1"
                    current_parent_cond = ""
                elif source_val == "Header":
                    current_parent_path = "Header"
                    current_parent_seg = ""
                    current_parent_cond = ""
                continue

            # ── Strikethrough & Crossed-Out Detection ──
            # Only true strikethrough XML runs or explicit textual exclusion triggers
            is_crossed = any(strikes)
            lower_notes = (notes + " " + ba_comment).lower()
            if any(term in lower_notes for term in (
                "not mapped by default",
                "commented out by default",
                "commented out",
                "[r3 is mapped but commented out",
            )):
                is_crossed = True
            elif source_val.strip().lower() in ("not mapped", "not mapped by default", "commented out", "n/a", "not used"):
                is_crossed = True
            elif ba_comment.strip().lower() in ("not mapped", "not mapped by default", "commented out"):
                is_crossed = True

            # Safeguards:
            # 1. Row has conditional IF...THEN logic (e.g. L108) -> NOT crossed out
            if re.search(r"\bif\b.*\bthen\b", source_val, re.I):
                is_crossed = False

            # 2. Destination element is explicitly L108 -> NOT crossed out
            if dest == "L108":
                is_crossed = False

            # 3. Explicitly added/active in BA comments or notes -> NOT crossed out
            lower_ba = ba_comment.strip().lower()
            if any(w in lower_ba.split() for w in ("add", "added", "active", "new", "include")) or lower_ba.startswith("add"):
                is_crossed = False

            # ── Element vs Segment / Loop Container Check ──
            # Elements have format like ST01, B302, C201, N901, G6201, L108, L301, S501 (ends with 2 digits)
            elem_match = re.match(r"^([A-Z][A-Z0-9]{1,3}?)(\d{2})$", dest)

            if not elem_match:
                # This is a segment or loop container row!
                # E.g. ST, B3, C2, C3, N9, G62, R3, K1, N1Loop1, N1, N3, N4, S5Loop1, S5, N7Loop1, N7, LXLoop1, LX, L5, L0, L1, L7, L3
                if dest:
                    clean_dest = dest.split("/")[0].strip()

                    # Only reset parent condition if we're moving to an entirely new top-level container/section
                    # Do NOT reset parent condition if moving between parent loop and its child segment (e.g. LXLoop1 -> LX, N1Loop1 -> N1)
                    is_subsegment_transition = (
                        (current_parent_seg in ("LXLoop1", "LX") and clean_dest in ("LXLoop1", "LX")) or
                        (current_parent_seg in ("N1Loop1", "N1") and clean_dest in ("N1Loop1", "N1")) or
                        (current_parent_seg in ("N7Loop1", "N7") and clean_dest in ("N7Loop1", "N7")) or
                        (current_parent_seg in ("S5Loop1", "S5") and clean_dest in ("S5Loop1", "S5"))
                    )

                    combined_container_text = f"{source_val} {ba_comment} {notes}".strip()
                    if is_lx_special_charge_filter(combined_container_text):
                        current_parent_cond = "RateAndCharges/@SpecialChargeOrAllowanceCode != '' (Exclude product line items)"
                    elif not is_subsegment_transition and not any(k in source_val for k in ("Where ", "If ", "when ")):
                        current_parent_cond = ""

                    current_parent_seg = dest

                    # Auto-assign proper canonical parent path for known segments
                    SEGMENT_CANONICAL_CONTAINERS = {
                        "ST": "Header/TransactionSetheader",
                        "B3": "Header/BeginningSegmentForCarriersInvoice",
                        "C2": "Header",
                        "C3": "Header/Currency",
                        "N9": "Header/ReferenceList",
                        "G62": "Header/DateTimes",
                        "R3": "Header",
                        "K1": "Header",
                        "N1Loop1": "Header/PartyList",
                        "N1": "Header/PartyList/Party",
                        "N3": "Header/PartyList/Party/AddressInformation",
                        "N4": "Header/PartyList/Party/GeographicLocation",
                        "N7Loop1": "Header/EquipmentList",
                        "N7": "Header/EquipmentList/Equipment",
                        "S5Loop1": "Detail/StopList",
                        "S5": "Detail/StopList",
                        "LXLoop1": "Detail/LineItemList",
                        "LX": "Detail/LineItemList/LineItem",
                        "L5": "Detail/LineItem/DescriptionMarksAndNumbers",
                        "L0": "Detail/LineItem/LineItemQuantityAndWeight",
                        "L1": "Detail/LineItem/RateAndCharges",
                        "L7": "Detail/LineItem/DescriptionMarksAndNumbers",
                        "L3": "Summary/TotalWeightAndCharges",
                        "SE": "Summary/TransactionSetTrailer",
                    }
                    if clean_dest in SEGMENT_CANONICAL_CONTAINERS:
                        current_parent_path = SEGMENT_CANONICAL_CONTAINERS[clean_dest]

                if source_val:
                    # Check if source contains a condition (e.g. "Where Name/@EntityIdentifierCode = BT" or "If commoditycode2 != NULL")
                    if is_lx_special_charge_filter(source_val):
                        current_parent_cond = "RateAndCharges/@SpecialChargeOrAllowanceCode != '' (Exclude product line items)"
                    elif any(k in source_val for k in ("Where ", "where ", "If ", "IF ", "when ", "When ")):
                        current_parent_cond = source_val
                    elif source_val not in ("Header", "Summary", "Detail/LineItem", "Detail"):
                        clean_path = re.sub(r"\s*/\s*", "/", source_val).strip()
                        if "Reference" in clean_path:
                            current_parent_path = "Header/ReferenceList"
                        else:
                            current_parent_path = clean_path

                if notes:
                    if is_lx_special_charge_filter(notes):
                        current_parent_cond = "RateAndCharges/@SpecialChargeOrAllowanceCode != '' (Exclude product line items)"
                    elif any(k in notes for k in ("Where ", "where ", "If ", "IF ", "when ", "When ")):
                        current_parent_cond = notes

                # Segment container rows are not mapping elements themselves
                continue

            # ── Valid Mapping Element Row ──
            seg_code = elem_match.group(1)
            element_code = dest

            # Disambiguate mapping IDs (e.g. multiple G6201 occurrences)
            count = id_counts.get(element_code, 0) + 1
            id_counts[element_code] = count
            mapping_id = f"MAP-{element_code}" if count == 1 else f"MAP-{element_code}-{count}"

            # ── Conditions Identification ──
            conditions: List[str] = []
            combined_elem_text = f"{source_val} {ba_comment} {notes}".strip()
            if is_lx_special_charge_filter(combined_elem_text) or is_lx_special_charge_filter(current_parent_cond):
                lx_cond = "RateAndCharges/@SpecialChargeOrAllowanceCode != '' (Exclude product line items)"
                if lx_cond not in conditions:
                    conditions.append(lx_cond)
                current_parent_cond = lx_cond

            if current_parent_cond and current_parent_cond not in conditions:
                conditions.append(current_parent_cond)

            # Check for element-level condition in source or notes
            elem_cond_match = re.search(r"(?:IF|If|where|Where|when|When)\s+.*", source_val)
            if elem_cond_match:
                elem_cond = elem_cond_match.group(0).strip()
                if elem_cond not in conditions:
                    conditions.append(elem_cond)

            if notes and any(k in notes for k in ("Where ", "where ", "If ", "IF ", "when ", "When ")):
                if notes not in conditions:
                    conditions.append(notes)

            # ── Constants, Static Values & Path Identification ──
            # Rule: "if there is no path means it is a constant"
            # Rule: "if it found hardcoded or related stuff it should harcode follow the parent condtions and paths"
            is_constant = False
            is_not_in_schema = False
            constants: List[str] = []
            canonical_path = ""
            suggested_path: Optional[str] = None
            path_correction_reason: Optional[str] = None
            schema_validation_status = "valid"
            transformations: List[str] = []
            qualifiers: List[str] = []
            loop_context = ""
            loop_relative_path = ""

            # Check for explicit hardcoded / literal patterns
            hardcoded_match = re.search(
                r"(?:Hardcoded\s+(?:value\s+of\s+)?to|Hardcoded\s+value\s+of|Literal|Hardcoded)\s+[\"']?([^\"'\n]+)[\"']?",
                source_val,
                re.I,
            )
            quoted_literals = re.findall(r"[\"']([A-Za-z0-9_-]+)[\"']", source_val)

            # Check for path tokens: / or @
            has_path_tokens = "/" in source_val or "@" in source_val
            lower_source = source_val.lower()

            if hardcoded_match:
                is_constant = True
                val = hardcoded_match.group(1).strip().strip("'\"")
                if val:
                    constants.append(val)
                schema_validation_status = "constant"
                loop_context, _ = self._canonical_resolver.get_loop_context_and_relative(element_code, "", current_parent_path)
            elif quoted_literals and not has_path_tokens:
                is_constant = True
                constants.extend(quoted_literals)
                schema_validation_status = "constant"
                loop_context, _ = self._canonical_resolver.get_loop_context_and_relative(element_code, "", current_parent_path)
            elif not source_val or lower_source in ("not mapped", "none by default"):
                is_constant = True
                schema_validation_status = "constant"
                loop_context, _ = self._canonical_resolver.get_loop_context_and_relative(element_code, "", current_parent_path)
            elif "position()" in lower_source or "position in loop" in lower_source:
                canonical_path = "position()"
                transformations.append("loop_position")
                loop_context, loop_relative_path = self._canonical_resolver.get_loop_context_and_relative(element_code, "position()", current_parent_path)
            elif not has_path_tokens and not any(k in lower_source for k in ("commodity", "tariff", "currency", "reference", "charge", "rate", "invoice", "date", "entity", "party", "name", "weight")):
                is_constant = True
                if source_val:
                    constants.append(source_val)
                schema_validation_status = "constant"
                loop_context, _ = self._canonical_resolver.get_loop_context_and_relative(element_code, "", current_parent_path)
            else:
                # Resolve Canonical Path using schema & diagnostics!
                diag = self._canonical_resolver.resolve_with_diagnostics(
                    source_val=source_val,
                    parent_path=current_parent_path,
                    destination_element=element_code,
                    transaction=transaction,
                )
                canonical_path = diag.canonical_path
                loop_context = diag.loop_context
                loop_relative_path = diag.loop_relative_path
                if diag.issue_type == "not_in_schema":
                    is_not_in_schema = True
                    schema_validation_status = "not_in_schema"
                    path_correction_reason = diag.reason
                    if diag.reason and diag.reason not in combined_notes:
                        combined_notes.append(f"[Schema Warning] {diag.reason}")

                    review_points.append(
                        ReviewPoint(
                            mapping_id=mapping_id,
                            destination_element=element_code,
                            destination_segment=seg_code,
                            source_document_reference=source_val,
                            source_canonical_path=canonical_path,
                            suggested_canonical_path=canonical_path,
                            loop_context=diag.loop_context,
                            loop_relative_path=diag.loop_relative_path,
                            suggested_loop_path=diag.suggested_loop_path,
                            issue_type="not_in_schema",
                            message=diag.reason,
                            confidence=diag.confidence,
                            status="pending_confirmation",
                        )
                    )
                elif diag.is_corrected:
                    suggested_path = diag.suggested_path
                    path_correction_reason = diag.reason
                    schema_validation_status = "corrected"
                    if diag.reason and diag.reason not in combined_notes:
                        combined_notes.append(f"[Schema Suggestion] {diag.reason}")

                    review_points.append(
                        ReviewPoint(
                            mapping_id=mapping_id,
                            destination_element=element_code,
                            destination_segment=seg_code,
                            source_document_reference=source_val,
                            source_canonical_path=canonical_path,
                            suggested_canonical_path=diag.suggested_path,
                            loop_context=diag.loop_context,
                            loop_relative_path=diag.loop_relative_path,
                            suggested_loop_path=diag.suggested_loop_path,
                            issue_type=diag.issue_type,
                            message=diag.reason,
                            confidence=diag.confidence,
                            status="applied",
                        )
                    )

            # Check for date / formatting transformations
            if any(term in (notes + " " + source_val).lower() for term in ("yyyymmdd", "date format", "format yyyymmdd")):
                transformations.append("format_date_YYYYMMDD")

            # Check for code translations / lookups
            has_table_ref = any("table" in txt.lower() for txt in (notes, ba_comment, source_val))
            has_inline_translation = bool(re.search(r"(?:translate|send)\s+['\"][A-Za-z0-9_-]+['\"]", source_val, re.I))
            is_pure_omission = bool(re.search(r"\bif\b.*\bthen\s+omit\b", source_val, re.I)) and not has_inline_translation and not has_table_ref

            if element_code in lookups and (has_table_ref or (has_inline_translation and not is_pure_omission)):
                for k, v in lookups[element_code].items():
                    transformations.append(f"code_map_{k}_to_{v}")

            # Check inline code translation: e.g. "when Name/@EntityIdentifierCode = 'SH' translate to 'SF'"
            trans_match = re.search(r"translate\s+to\s+[\"']?([A-Za-z0-9_-]+)[\"']?", source_val, re.I)
            if trans_match:
                qualifiers.append(trans_match.group(1))

            # ── Implementation Status ──
            if is_crossed:
                status = "excluded_crossed_out"
            elif is_constant:
                status = "constant_value"
            elif canonical_path:
                status = "unresolved"
            else:
                status = "requires_user_clarification"

            rec = MappingRecord(
                mapping_id=mapping_id,
                source_document_reference=source_val or "not_specified",
                source_description=ba_comment or source_val or element_code,
                source_canonical_path=canonical_path,
                destination_segment=seg_code,
                destination_element=element_code,
                mapping_rule=source_val or ("Excluded" if is_crossed else ("Constant value" if is_constant else "Direct mapping")),
                conditions=conditions,
                constants=constants,
                transformations=transformations,
                qualifiers=qualifiers,
                default_behavior="omit" if is_crossed else ("constant" if is_constant else "direct"),
                related_notes=combined_notes,
                source_path_resolution_status="resolved" if (canonical_path or is_constant) else "unresolved",
                destination_schema_status="resolved",
                ambiguities=[] if (canonical_path or is_constant or is_crossed) else ["Missing source path"],
                implementation_status=status,
                is_crossed=is_crossed,
                is_constant=is_constant,
                is_not_in_schema=is_not_in_schema,
                parent_segment=current_parent_seg,
                parent_path=current_parent_path,
                parent_condition=current_parent_cond,
                loop_context=loop_context,
                loop_relative_path=loop_relative_path,
                extraction_method="python",
                suggested_canonical_path=suggested_path,
                path_correction_reason=path_correction_reason,
                schema_validation_status=schema_validation_status,
            )
            mappings.append(rec)

        return mappings, review_points

    def _resolve_canonical_path(self, source_val: str, parent_path: str) -> str:
        """
        Hierarchically resolves canonical path using the CanonicalPathResolver.
        Specialized for canonical schema: DescriptionMarksAndNumbers (CommodityCode2),
        TariffReference (TariffDistance, DistanceQualifier), RateAndCharges, etc.
        """
        return self._canonical_resolver.resolve_canonical_path(source_val, parent_path)

    def _get_cell_text(self, tc: ET.Element) -> tuple[str, bool]:
        """
        Returns cell text and whether the cell contains strikethrough runs or del tags.
        """
        text_parts = []
        has_strike = False

        # Check for deleted change tracking: <w:del>
        if tc.findall(".//w:del", DOCX_NS):
            has_strike = True

        for r in tc.findall(".//w:r", DOCX_NS):
            t = "".join(r.itertext())
            text_parts.append(t)
            if r.findall(".//w:strike", DOCX_NS) or r.findall(".//w:dstrike", DOCX_NS):
                has_strike = True

        if tc.findall(".//w:strike", DOCX_NS) or tc.findall(".//w:dstrike", DOCX_NS):
            has_strike = True

        return "".join(text_parts).strip(), has_strike

    def _normalize_text(self, text: str) -> str:
        """
        Normalizes smart quotes, unusual whitespace, and control chars.
        """
        if not text:
            return ""
        t = (
            text.replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
            .replace("–", "-")
            .replace("—", "-")
            .replace("\r", " ")
            .replace("\n", " ")
        )
        return re.sub(r"\s+", " ", t).strip()

    def _extract_lookup_translations(self, lookup_tables: List[ET.Element]) -> Dict[str, Dict[str, str]]:
        """
        Extracts code translations from auxiliary tables in the docx.
        E.g. Table 3: RateAndCharges/@SpecialChargeOrAllowanceCode 405 -> L108 FUE
        Rejects non-code entries, documentation fallbacks (e.g. 'Else' -> 'Copy Value'), and long descriptions.
        """
        translations: Dict[str, Dict[str, str]] = {}
        INVALID_CODE_WORDS = {
            "else", "otherwise", "default", "none", "copy", "null", "all",
            "all others", "any", "other", "value", "empty", "omit",
            "not mapped", "n/a", "element", "hardcode", "hardcoded",
            "commented out", "blank"
        }
        for tbl in lookup_tables:
            rows = tbl.findall("./w:tr", DOCX_NS)
            if len(rows) < 2:
                continue
            header_cells = [self._get_cell_text(c)[0] for c in rows[0].findall("./w:tc", DOCX_NS)]
            target_col = -1
            source_col = -1

            for c_idx, h in enumerate(header_cells):
                if re.match(r"^[A-Z][A-Z0-9]{1,3}\d{2}$", h.strip()):
                    target_col = c_idx
                elif any(k in h.lower() for k in ("code", "charge", "reference", "@")):
                    source_col = c_idx

            if target_col >= 0 and source_col >= 0:
                elem_name = header_cells[target_col].strip()
                if elem_name not in translations:
                    translations[elem_name] = {}
                for r in rows[1:]:
                    cells = [self._get_cell_text(c)[0] for c in r.findall("./w:tc", DOCX_NS)]
                    if len(cells) > max(source_col, target_col):
                        src_val = cells[source_col].strip()
                        tgt_val = cells[target_col].strip()
                        if not src_val or not tgt_val:
                            continue
                        # Strictly reject invalid code tokens / instructions
                        if src_val.lower() in INVALID_CODE_WORDS or tgt_val.lower() in INVALID_CODE_WORDS:
                            continue
                        if "@" in src_val or "@" in tgt_val:
                            continue
                        if " " in src_val or " " in tgt_val:
                            continue
                        if any(term in tgt_val.lower() for term in ("copy", "omit", "value", "element", "default", "none")):
                            continue
                        if any(term in src_val.lower() for term in ("copy", "omit", "value", "element", "default", "none")):
                            continue
                        if len(src_val) > 12 or len(tgt_val) > 12:
                            continue
                        translations[elem_name][src_val] = tgt_val
        return translations

    def _parse_xlsx(self, path: Path, transaction: str) -> MappingSpecification:
        # Fallback for XLSX if user uploads Excel
        raise NotImplementedError("Excel matrix format (.xlsx) not yet supported. Please upload .docx")

    def _parse_csv(self, path: Path, transaction: str) -> MappingSpecification:
        # Fallback for CSV if user uploads CSV
        raise NotImplementedError("CSV matrix format not yet supported. Please upload .docx")
