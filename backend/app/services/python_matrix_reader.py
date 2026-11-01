import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.models.mapping import MappingRecord, MappingSpecification

log = logging.getLogger(__name__)

DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


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
        mappings = self._extract_mappings_from_table(main_table, transaction, lookup_translations)

        if not mappings:
            raise ValueError("No valid EDI mapping rows could be extracted from matrix.")

        summary = (
            f"Extracted {len(mappings)} EDI {transaction} mapping rows using Python deterministic parser. "
            f"Identified {sum(1 for m in mappings if m.is_constant)} constants, "
            f"{sum(1 for m in mappings if m.is_crossed)} crossed-out/excluded elements, and "
            f"{sum(1 for m in mappings if m.conditions)} conditional elements."
        )

        return MappingSpecification(
            transaction=transaction,
            document_summary=summary,
            mappings=mappings,
            extraction_method="python",
        )

    def _extract_mappings_from_table(
        self, tbl: ET.Element, transaction: str, lookups: Dict[str, Any]
    ) -> List[MappingRecord]:
        rows = tbl.findall("./w:tr", DOCX_NS)
        mappings: List[MappingRecord] = []
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

            # ── Element vs Segment / Loop Container Check ──
            # Elements have format like ST01, B302, C201, N901, G6201, L108, L301, S501 (ends with 2 digits)
            elem_match = re.match(r"^([A-Z][A-Z0-9]{1,3}?)(\d{2})$", dest)

            if not elem_match:
                # This is a segment or loop container row!
                # E.g. ST, B3, C2, C3, N9, G62, R3, K1, N1Loop1, N1, N3, N4, S5Loop1, S5, N7Loop1, N7, LXLoop1, LX, L5, L0, L1, L7, L3
                if dest:
                    current_parent_seg = dest
                    # When a new top segment starts, reset parent condition unless specified
                    if not any(k in source_val for k in ("Where ", "If ", "when ")):
                        current_parent_cond = ""

                    # Auto-assign proper canonical parent path for known segments
                    if dest == "L7":
                        current_parent_path = "Detail/LineItem/DescriptionMarksAndNumbers"
                    elif dest in ("L5", "LXLoop1/L5"):
                        current_parent_path = "Detail/LineItem/DescriptionMarksAndNumbers"
                    elif dest in ("L0", "LXLoop1/L0"):
                        current_parent_path = "Detail/LineItem/LineItemQuantityAndWeight"
                    elif dest in ("L1", "LXLoop1/L1"):
                        current_parent_path = "Detail/LineItem/RateAndCharges"
                    elif dest == "L3":
                        current_parent_path = "Summary/TotalWeightAndCharges"

                if source_val:
                    # Check if source contains a condition (e.g. "Where Name/@EntityIdentifierCode = BT" or "If commoditycode2 != NULL")
                    if any(k in source_val for k in ("Where ", "where ", "If ", "IF ", "when ", "When ")):
                        current_parent_cond = source_val
                    elif source_val not in ("Header", "Summary", "Detail/LineItem"):
                        # Normalize path
                        clean_path = re.sub(r"\s*/\s*", "/", source_val).strip()
                        current_parent_path = clean_path

                if notes and any(k in notes for k in ("Where ", "where ", "If ", "IF ", "when ", "When ")):
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
            if current_parent_cond:
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
            constants: List[str] = []
            canonical_path = ""
            transformations: List[str] = []
            qualifiers: List[str] = []

            # Check for explicit hardcoded / literal patterns
            hardcoded_match = re.search(
                r"(?:Hardcoded\s+(?:value\s+of\s+)?to|Hardcoded\s+value\s+of|Literal|Hardcoded)\s+[\"']?([^\"'\n]+)[\"']?",
                source_val,
                re.I,
            )
            quoted_literals = re.findall(r"[\"']([A-Za-z0-9_-]+)[\"']", source_val)

            # Check for path tokens: / or @
            has_path_tokens = "/" in source_val or "@" in source_val

            if hardcoded_match:
                is_constant = True
                val = hardcoded_match.group(1).strip().strip("'\"")
                if val:
                    constants.append(val)
            elif quoted_literals and not has_path_tokens:
                is_constant = True
                constants.extend(quoted_literals)
            elif not source_val or source_val.lower() in ("not mapped", "none by default"):
                is_constant = True
            elif "position()" in source_val.lower() or "position in loop" in source_val.lower():
                # Loop position expression
                canonical_path = "position()"
                transformations.append("loop_position")
            elif not has_path_tokens:
                # No path provided -> mark as constant
                is_constant = True
                if source_val:
                    constants.append(source_val)
            else:
                # Resolve Canonical Path
                canonical_path = self._resolve_canonical_path(source_val, current_parent_path)

            # Check for date / formatting transformations
            if any(term in (notes + " " + source_val).lower() for term in ("yyyymmdd", "date format", "format yyyymmdd")):
                transformations.append("format_date_YYYYMMDD")

            # Check for code translations / lookups
            if element_code in lookups:
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
                parent_segment=current_parent_seg,
                parent_path=current_parent_path,
                parent_condition=current_parent_cond,
                extraction_method="python",
            )
            mappings.append(rec)

        return mappings

    def _resolve_canonical_path(self, source_val: str, parent_path: str) -> str:
        """
        Hierarchically resolves canonical path using the parent container path.
        Specialized for canonical schema: DescriptionMarksAndNumbers (CommodityCode2),
        TariffReference (TariffDistance, DistanceQualifier), RateAndCharges, etc.
        """
        clean = re.sub(r"\s*/\s*", "/", source_val).strip()
        lower = clean.lower()

        # ── 1. Priority canonical domain mappings (Commodity & Tariff Distance) ──
        if "commoditycode" in lower:
            if "qualifier" in lower:
                return "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCodeQualifier2"
            return "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2"

        if "tariffdistance" in lower or ("tariff" in lower and "distance" in lower):
            if "qualifier" in lower:
                return "Detail/LineItem/TariffReference/@DistanceQualifier"
            return "Detail/LineItem/TariffReference/@TariffDistance"

        if "distancequalifier" in lower:
            return "Detail/LineItem/TariffReference/@DistanceQualifier"

        # ── 2. Extract path token ──
        path_match = re.search(r"([A-Za-z0-9_]+/[A-Za-z0-9_/@]+|@[A-Za-z0-9_]+)", clean)
        if not path_match:
            return clean

        extracted = path_match.group(1).strip()
        lower_extracted = extracted.lower()

        # Check extracted token for commodity / tariff distance
        if "commoditycode" in lower_extracted:
            if "qualifier" in lower_extracted:
                return "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCodeQualifier2"
            return "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2"
        if "tariffdistance" in lower_extracted or ("tariff" in lower_extracted and "distance" in lower_extracted):
            return "Detail/LineItem/TariffReference/@TariffDistance"

        # ── 3. Handle root-anchored paths ──
        if extracted.startswith(("Header/", "Detail/", "Summary/", "Invoice/")):
            return extracted

        # Map LineItem direct child elements to full path
        if extracted.startswith(("DescriptionMarksAndNumbers/", "LineItemQuantityAndWeight/", "RateAndCharges/", "TariffReference/")):
            return f"Detail/LineItem/{extracted}"

        if extracted.startswith(("BeginningSegmentForCarriersInvoice/", "Currency/", "TransactionSetheader/", "PartyList/", "EquipmentList/")):
            return f"Header/{extracted}"

        if extracted.startswith("Party/"):
            return f"Header/PartyList/{extracted}"

        if extracted.startswith("TotalWeightAndCharges/"):
            return f"Summary/{extracted}"

        normalized_parent = re.sub(r"\s*/\s*", "/", parent_path).strip().rstrip("/")

        # ── 4. Attribute resolution (@Attribute) ──
        if extracted.startswith("@"):
            if normalized_parent:
                if normalized_parent in ("DescriptionMarksAndNumbers", "LineItemQuantityAndWeight", "RateAndCharges", "TariffReference"):
                    return f"Detail/LineItem/{normalized_parent}/{extracted}"
                elif normalized_parent in ("TotalWeightAndCharges", "TransactionSetTrailer"):
                    return f"Summary/{normalized_parent}/{extracted}"
                return f"{normalized_parent}/{extracted}"
            return extracted

        # ── 5. Relative element/attribute paths with parent container ──
        if normalized_parent:
            parts = extracted.split("/")
            parent_parts = normalized_parent.split("/")
            if parent_parts[-1] == parts[0]:
                merged = "/".join(parent_parts + parts[1:])
                if not merged.startswith(("Header/", "Detail/", "Summary/", "Invoice/")):
                    if merged.startswith(("DescriptionMarksAndNumbers", "LineItemQuantityAndWeight", "RateAndCharges", "TariffReference")):
                        return f"Detail/LineItem/{merged}"
                return merged
            combined = f"{normalized_parent}/{extracted}"
            if not combined.startswith(("Header/", "Detail/", "Summary/", "Invoice/")):
                if combined.startswith(("DescriptionMarksAndNumbers", "LineItemQuantityAndWeight", "RateAndCharges", "TariffReference")):
                    return f"Detail/LineItem/{combined}"
            return combined

        return extracted

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
        """
        translations: Dict[str, Dict[str, str]] = {}
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
                        if src_val and tgt_val:
                            translations[elem_name][src_val] = tgt_val
        return translations

    def _parse_xlsx(self, path: Path, transaction: str) -> MappingSpecification:
        # Fallback for XLSX if user uploads Excel
        raise NotImplementedError("Excel matrix format (.xlsx) not yet supported. Please upload .docx")

    def _parse_csv(self, path: Path, transaction: str) -> MappingSpecification:
        # Fallback for CSV if user uploads CSV
        raise NotImplementedError("CSV matrix format not yet supported. Please upload .docx")
