from pathlib import Path
import re
import difflib
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any, List, Set, Tuple
from lxml import etree
from app.services.xslt_analysis_service import PARSER


class PathResolutionResult:
    """Encapsulates the resolution and diagnostics of a canonical XML path."""

    def __init__(
        self,
        canonical_path: str,
        is_valid: bool = True,
        is_corrected: bool = False,
        original_input: str = "",
        suggested_path: Optional[str] = None,
        issue_type: str = "none",  # "spelling" | "container_structure" | "path_completion" | "none"
        reason: str = "",
        confidence: float = 1.0,
        loop_context: str = "",
        loop_relative_path: str = "",
        suggested_loop_path: Optional[str] = None,
    ):
        self.canonical_path = canonical_path
        self.is_valid = is_valid
        self.is_corrected = is_corrected
        self.original_input = original_input
        self.suggested_path = suggested_path or canonical_path
        self.issue_type = issue_type
        self.reason = reason
        self.confidence = confidence
        self.loop_context = loop_context
        self.loop_relative_path = loop_relative_path
        self.suggested_loop_path = suggested_loop_path or loop_relative_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_path": self.canonical_path,
            "is_valid": self.is_valid,
            "is_corrected": self.is_corrected,
            "original_input": self.original_input,
            "suggested_path": self.suggested_path,
            "issue_type": self.issue_type,
            "reason": self.reason,
            "confidence": self.confidence,
            "loop_context": self.loop_context,
            "loop_relative_path": self.loop_relative_path,
            "suggested_loop_path": self.suggested_loop_path,
        }


class CanonicalPathResolver:
    """
    Authoritative Canonical Schema & Test File Path Resolver.
    Validates and corrects canonical XML paths using:
    - Authoritative canonical schema (InvoiceCanonicalSchema.xsd)
    - Authoritative canonical test files (210_canonical_test.xml)
    - Built-in canonical domain knowledge
    - Fuzzy spelling matching and container structure correction
    """

    CANONICAL_KNOWN_PATHS: Dict[str, str] = {
        # Detail / LineItem - Commodity & Tariff Reference
        "commoditycode2": "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2",
        "commoditycodequalifier2": "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCodeQualifier2",
        "commoditycode": "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode",
        "commoditycodequalifier": "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCodeQualifier",
        "tariffdistance": "Detail/LineItem/TariffReference/@TariffDistance",
        "distancequalifier": "Detail/LineItem/TariffReference/@DistanceQualifier",
        "tariffsection": "Detail/LineItem/TariffReference/@TariffSection",
        "freightclasscode": "Detail/LineItem/TariffReference/@FreightClassCode",
        "tariffagencycode": "Detail/LineItem/TariffReference/@TariffAgencyCode",
        "tariffnumber": "Detail/LineItem/TariffReference/@TariffNumber",

        # Detail / LineItem - Rate & Charges
        "specialchargeorallowancecode": "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode",
        "freightrate": "Detail/LineItem/RateAndCharges/@FreightRate",
        "ratevaluequalifier": "Detail/LineItem/RateAndCharges/@RateValueQualifier",
        "charge": "Detail/LineItem/RateAndCharges/@Charge",
        "ratecombinationpointcode": "Detail/LineItem/RateAndCharges/@RateCombinationPointCode",

        # Detail / LineItem - Quantities, Weights & Descriptions
        "assignednumber": "Detail/LineItem/AssignedNumber/@AssignedNumber",
        "ladinglineitemnumber": "Detail/LineItem/DescriptionMarksAndNumbers/@LadingLineItemNumber",
        "ladingdescription": "Detail/LineItem/DescriptionMarksAndNumbers/@LadingDescription",
        "billedratedasquantity": "Detail/LineItem/LineItemQuantityAndWeight/@BilledRatedAsQuantity",
        "billedratedasqualifier": "Detail/LineItem/LineItemQuantityAndWeight/@BilledRatedAsQualifier",
        "weight": "Detail/LineItem/LineItemQuantityAndWeight/@Weight",
        "weightqualifier": "Detail/LineItem/LineItemQuantityAndWeight/@WeightQualifier",
        "ladingquantity": "Detail/LineItem/LineItemQuantityAndWeight/@LadingQuantity",
        "ladingquantitypackagingformcode": "Detail/LineItem/LineItemQuantityAndWeight/@LadingQuantityPackagingFormCode",
        "weightunitcode": "Detail/LineItem/LineItemQuantityAndWeight/@WeightUnitCode",

        # Header - Beginning Segment
        "shipmentqualifier": "Header/BeginningSegmentForCarriersInvoice/@ShipmentQualifier",
        "invoicenumber": "Header/BeginningSegmentForCarriersInvoice/@InvoiceNumber",
        "shipmentidentificationnumber": "Header/BeginningSegmentForCarriersInvoice/@ShipmentIdentificationNumber",
        "shipmentmethodofpayment": "Header/BeginningSegmentForCarriersInvoice/@ShipmentMethodOfPayment",
        "invoicedate": "Header/BeginningSegmentForCarriersInvoice/@InvoiceDate",
        "netamountdue": "Header/BeginningSegmentForCarriersInvoice/@NetAmountDue",
        "deliverydate": "Header/BeginningSegmentForCarriersInvoice/@DeliveryDate",
        "datetimequalifier": "Header/BeginningSegmentForCarriersInvoice/@DateTimeQualifier",
        "standardcarrieralphacode": "Header/BeginningSegmentForCarriersInvoice/@StandardCarrierAlphaCode",
        "billingdate": "Header/BeginningSegmentForCarriersInvoice/@BillingDate",
        "pickupdate": "Header/BeginningSegmentForCarriersInvoice/@PickupDate",
        "correctionindicator": "Header/BeginningSegmentForCarriersInvoice/@CorrectionIndicator",
        "tariffservicecode": "Header/BeginningSegmentForCarriersInvoice/@TariffServiceCode",
        "transportationtermscode": "Header/BeginningSegmentForCarriersInvoice/@TransportationTermsCode",

        # Header - Currency & Reference
        "billingcurrencycode": "Header/Currency/@BillingCurrencyCode",
        "transactionsetidentifiercode": "Header/TransactionSetheader/@TransactionSetIdentifierCode",
        "transactionsetcontrolnumber": "Header/TransactionSetheader/@TransactionSetControlNumber",
        "transactionsetname": "Header/TransactionSetheader/@TransactionSetName",
        "referenceinformation": "Header/ReferenceList/ReferenceInformation/@ReferenceInformation",
        "referenceinformationqualifier": "Header/ReferenceList/ReferenceInformation/@ReferenceInformationQualifier",
        "edicode": "Header/ReferenceList/ReferenceInformation/@EDICode",

        # Header - Parties & Locations
        "entityidentifiercode": "Header/PartyList/Party/Name/@EntityIdentifierCode",
        "name": "Header/PartyList/Party/Name/@Name",
        "addressinformationline1": "Header/PartyList/Party/AddressInformation/@AddressInformationLine1",
        "addressinformationline2": "Header/PartyList/Party/AddressInformation/@AddressInformationLine2",
        "cityname": "Header/PartyList/Party/GeographicLocation/@CityName",
        "stateorprovincecode": "Header/PartyList/Party/GeographicLocation/@StateOrProvinceCode",
        "postalcode": "Header/PartyList/Party/GeographicLocation/@PostalCode",
        "countrycode": "Header/PartyList/Party/GeographicLocation/@CountryCode",

        # Header - Equipment
        "equipmentnumber": "Header/EquipmentList/Equipment/@EquipmentNumber",
        "equipmenttype": "Header/EquipmentList/Equipment/@EquipmentType",
        "equipmentdescription": "Header/EquipmentList/Equipment/@EquipmentDescription",
        "equipmentdescriptioncode": "Header/EquipmentList/Equipment/@EquipmentDescriptionCode",
        "equipmentlength": "Header/EquipmentList/Equipment/@EquipmentLength",

        # Summary
        "totalcharges": "Summary/TotalWeightAndCharges/@TotalCharges",
        "numberofincludedsegments": "Summary/TransactionSetTrailer/@NumberOfIncludedSegments",
        "transactionsetcontrolnumber_summary": "Summary/TransactionSetTrailer/@TransactionSetControlNumber",
    }

    def __init__(self):
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    def _get_schema_data(self, transaction: str = "210") -> Dict[str, Any]:
        """Loads and indexes elements, complexTypes, and test paths from schema and reference files."""
        if transaction in self._schema_cache:
            return self._schema_cache[transaction]

        leaf_map: Dict[str, str] = dict(self.CANONICAL_KNOWN_PATHS)
        valid_paths: Set[str] = set(self.CANONICAL_KNOWN_PATHS.values())
        element_names: Set[str] = set()
        xsd_name = "InvoiceCanonicalSchema.xsd"

        # Find reference directories
        candidate_dirs = [
            Path(__file__).resolve().parents[3] / "reference-files" / transaction,
            Path(__file__).resolve().parents[2] / "data" / "references" / transaction,
            Path("reference-files") / transaction,
            Path("../reference-files") / transaction,
            Path("backend/data/references") / transaction,
        ]
        ref_dirs = [d for d in candidate_dirs if d.exists() and d.is_dir()]

        for ref_dir in ref_dirs:
            # 1. Parse canonical test XML if present
            test_xml = ref_dir / f"{transaction}_canonical_test.xml"
            if not test_xml.exists():
                for f in ref_dir.glob("*_test.xml"):
                    test_xml = f
                    break

            if test_xml.exists():
                try:
                    tree = ET.parse(test_xml)
                    root = tree.getroot()
                    ns_strip = lambda tag: tag.split("}")[-1] if "}" in tag else tag

                    def walk(el: ET.Element, cur_path: str):
                        tag = ns_strip(el.tag)
                        p = f"{cur_path}/{tag}" if cur_path else tag
                        for attr in el.attrib:
                            full_attr_path = f"{p}/@{attr}"
                            # strip root prefix if Invoice
                            cleaned_p = full_attr_path.removeprefix("Invoice/").removeprefix("ns0:Invoice/")
                            valid_paths.add(cleaned_p)
                            clean_leaf = re.sub(r"[^a-zA-Z0-9]", "", attr).lower()
                            if clean_leaf not in leaf_map:
                                leaf_map[clean_leaf] = cleaned_p
                        for ch in el:
                            walk(ch, p)

                    walk(root, "")
                except Exception:
                    pass

            # 2. Parse Canonical XSD if present (full complexType and element expansion)
            for xsd_file in ref_dir.glob("**/*.xsd"):
                if "x12" in xsd_file.name.lower():
                    continue
                xsd_name = xsd_file.name
                try:
                    tree = ET.parse(xsd_file)
                    ns = {"xs": "http://www.w3.org/2001/XMLSchema"}

                    # Index all complexTypes and their child elements
                    types: Dict[str, List[Tuple[str, Optional[str]]]] = {}
                    for ct in tree.findall(".//xs:complexType", ns):
                        t_name = ct.get("name")
                        if t_name:
                            children = []
                            for el in ct.findall(".//xs:element", ns):
                                el_name = el.get("name")
                                el_type = el.get("type")
                                if el_name:
                                    children.append((el_name, el_type))
                            types[t_name] = children

                    # Recursively expand schema hierarchy to populate all valid canonical paths
                    def expand_type(type_name: str, cur_path: str, visited: Optional[Set[str]] = None):
                        if visited is None:
                            visited = set()
                        if type_name in visited:
                            return
                        visited = visited | {type_name}

                        for el_name, el_type in types.get(type_name, []):
                            element_names.add(el_name)
                            clean_leaf = re.sub(r"[^a-zA-Z0-9]", "", el_name).lower()

                            p = f"{cur_path}/{el_name}" if cur_path else el_name
                            p_clean = p.removeprefix("Invoice/").removeprefix("ns0:Invoice/")
                            valid_paths.add(p_clean)

                            p_attr = f"{cur_path}/@{el_name}" if cur_path else f"@{el_name}"
                            p_attr_clean = p_attr.removeprefix("Invoice/").removeprefix("ns0:Invoice/")
                            valid_paths.add(p_attr_clean)

                            parts = p_clean.split("/")
                            if len(parts) >= 2:
                                valid_paths.add(f"{parts[-2]}/@{parts[-1]}")
                                valid_paths.add(f"{parts[-2]}/{parts[-1]}")

                            if clean_leaf not in leaf_map:
                                leaf_map[clean_leaf] = p_attr_clean

                            if el_type and el_type in types:
                                expand_type(el_type, p, visited)

                    if "InvoiceType" in types:
                        expand_type("InvoiceType", "")
                    else:
                        for ct_name in types:
                            expand_type(ct_name, "")

                    # Also index any direct elements / attributes
                    for el in tree.findall(".//xs:element", ns):
                        name = el.get("name")
                        if name:
                            element_names.add(name)
                            clean_name = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
                            if clean_name in self.CANONICAL_KNOWN_PATHS:
                                leaf_map[clean_name] = self.CANONICAL_KNOWN_PATHS[clean_name]

                    for attr in tree.findall(".//xs:attribute", ns):
                        attr_name = attr.get("name")
                        if attr_name:
                            element_names.add(attr_name)
                            clean_name = re.sub(r"[^a-zA-Z0-9]", "", attr_name).lower()
                            if clean_name in self.CANONICAL_KNOWN_PATHS:
                                leaf_map[clean_name] = self.CANONICAL_KNOWN_PATHS[clean_name]

                except Exception:
                    pass

        schema_data = {
            "leaf_map": leaf_map,
            "valid_paths": valid_paths,
            "element_names": element_names,
            "xsd_name": xsd_name,
        }
        self._schema_cache[transaction] = schema_data
        return schema_data

    @staticmethod
    def get_loop_context_and_relative(
        destination_element: str,
        canonical_path: str,
        parent_path: str = "",
    ) -> Tuple[str, str]:
        """
        Determines the enclosing loop context and the context-relative XPath expression
        evaluated within that loop's xsl:for-each.
        """
        dest_prefix = destination_element[:2] if len(destination_element) >= 2 else destination_element
        clean_path = canonical_path.strip().lstrip("/")

        # LineItem loop: LX, L0, L1, L5, L7, L4
        if dest_prefix in ("LX", "L0", "L1", "L5", "L7", "L4") or "LineItem" in clean_path or "LineItem" in parent_path:
            loop_context = "Detail/LineItemList/LineItem"
            if "LineItem/" in clean_path:
                rel = clean_path.split("LineItem/")[-1]
            elif "LineItemList/" in clean_path:
                rel = clean_path.split("LineItemList/")[-1]
            else:
                rel = clean_path
            return loop_context, rel

        # Party loop: N1, N2, N3, N4
        if dest_prefix in ("N1", "N2", "N3", "N4") or "Party" in clean_path or "Party" in parent_path:
            loop_context = "Header/PartyList/Party"
            if "Party/" in clean_path:
                rel = clean_path.split("Party/")[-1]
            else:
                rel = clean_path
            return loop_context, rel

        # Reference loop: N9
        if dest_prefix == "N9" or "ReferenceInformation" in clean_path or "ReferenceList" in clean_path:
            loop_context = "Header/ReferenceList/ReferenceInformation"
            if "ReferenceInformation/" in clean_path:
                rel = clean_path.split("ReferenceInformation/")[-1]
            elif "@" in clean_path:
                rel = "@" + clean_path.split("@")[-1]
            else:
                rel = clean_path
            return loop_context, rel

        # Equipment loop: N7
        if dest_prefix == "N7" or "Equipment" in clean_path:
            loop_context = "Header/EquipmentList/Equipment"
            if "Equipment/" in clean_path:
                rel = clean_path.split("Equipment/")[-1]
            elif "@" in clean_path:
                rel = "@" + clean_path.split("@")[-1]
            else:
                rel = clean_path
            return loop_context, rel

        # Stop list loop: S5
        if dest_prefix == "S5" or "StopList" in clean_path:
            loop_context = "Detail/StopList/Stop"
            if "Stop/" in clean_path:
                rel = clean_path.split("Stop/")[-1]
            else:
                rel = clean_path
            return loop_context, rel

        # Summary
        if dest_prefix in ("L3", "SE") or clean_path.startswith("Summary/"):
            return "Summary", clean_path

        # Header root
        return "Header", clean_path

    def resolve_known_path(self, field_name: str) -> Optional[str]:
        """Resolves authoritative canonical path for known domain attributes."""
        if not field_name:
            return None
        clean = re.sub(r"[^a-zA-Z0-9]", "", field_name).lower()
        return self.CANONICAL_KNOWN_PATHS.get(clean)

    def resolve_with_diagnostics(
        self,
        source_val: str,
        parent_path: str = "",
        destination_element: str = "",
        transaction: str = "210",
    ) -> PathResolutionResult:
        """
        Validates and resolves a matrix source path against the authoritative canonical schema.
        Detects typos, structural/container errors, and incomplete paths, providing clear suggestions
        that consider the enclosing parent loop (xsl:for-each) and context-relative XPath.
        """
        def _make_result(
            canonical: str,
            is_valid: bool = True,
            is_corrected: bool = False,
            suggested: Optional[str] = None,
            issue_type: str = "none",
            reason: str = "",
            confidence: float = 1.0,
        ) -> PathResolutionResult:
            sug = suggested or canonical
            loop_ctx, loop_rel = self.get_loop_context_and_relative(destination_element, canonical, parent_path)
            sug_ctx, sug_rel = self.get_loop_context_and_relative(destination_element, sug, parent_path)

            enhanced_reason = reason
            if is_corrected and enhanced_reason and "loop" not in enhanced_reason.lower():
                if loop_ctx not in ("Header", "Summary"):
                    enhanced_reason += f" (Enclosing Loop: '{loop_ctx}', Relative XPath: '{sug_rel}')"
                else:
                    enhanced_reason += f" (Context: '{loop_ctx}')"

            return PathResolutionResult(
                canonical_path=canonical,
                is_valid=is_valid,
                is_corrected=is_corrected,
                original_input=source_val,
                suggested_path=sug,
                issue_type=issue_type,
                reason=enhanced_reason,
                confidence=confidence,
                loop_context=loop_ctx,
                loop_relative_path=loop_rel,
                suggested_loop_path=sug_rel,
            )

        if not source_val:
            return _make_result("", is_valid=True, is_corrected=False)

        clean = re.sub(r"\s*/\s*", "/", source_val).strip()
        lower = clean.lower()
        schema_data = self._get_schema_data(transaction)
        leaf_map = schema_data["leaf_map"]
        valid_paths = schema_data["valid_paths"]

        # Loop position expression
        if lower in ("position()", "position in loop", "position() in loop"):
            return _make_result("position()", is_valid=True, is_corrected=False)

        # ── 1. Priority Domain Overrides (Commodity, Tariff, References, Currencies, Non-Schema Attributes) ──

        # Volume (L006) - Not in Canonical Schema
        if destination_element == "L006" or ("volume" in lower and "qualifier" not in lower and "unit" not in lower):
            canonical = "Detail/LineItem/LineItemQuantityAndWeight/@Volume"
            reason = (
                "Attribute '@Volume' (L006) is not defined in Canonical Schema (InvoiceCanonicalSchema.xsd under LineItemQuantityAndWeight). "
                "Confirm whether to ignore this mapping or keep it from matrix."
            )
            return _make_result(
                canonical,
                is_valid=False,
                is_corrected=False,
                suggested=canonical,
                issue_type="not_in_schema",
                reason=reason,
                confidence=0.95,
            )

        # Volume Unit Qualifier (L007) - Not in Canonical Schema
        if destination_element == "L007" or ("volume" in lower and ("qualifier" in lower or "unit" in lower)):
            canonical = "Detail/LineItem/LineItemQuantityAndWeight/@VolumeUnitQualifier"
            reason = (
                "Attribute '@VolumeUnitQualifier' (L007) is not defined in Canonical Schema (InvoiceCanonicalSchema.xsd under LineItemQuantityAndWeight). "
                "Confirm whether to ignore this mapping or keep it from matrix."
            )
            return _make_result(
                canonical,
                is_valid=False,
                is_corrected=False,
                suggested=canonical,
                issue_type="not_in_schema",
                reason=reason,
                confidence=0.95,
            )

        # CommodityCode & CommodityCodeQualifier
        if destination_element == "L707" or ("commoditycode" in lower and "qualifier" not in lower and destination_element != "L702"):
            canonical = "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2"
            if clean != canonical:
                is_spelling = "comodity" in lower or "commodity" in lower and "@CommodityCode2" not in clean
                issue = "spelling" if is_spelling else "path_completion"
                reason = (
                    f"Spelling '{source_val}' corrected to schema attribute '@CommodityCode2' in Detail/LineItem/DescriptionMarksAndNumbers"
                    if is_spelling
                    else f"Canonical container prepended to '{source_val}' -> {canonical}"
                )
                return _make_result(
                    canonical, is_valid=True, is_corrected=True,
                    suggested=canonical, issue_type=issue, reason=reason, confidence=0.96,
                )
            return _make_result(canonical, is_valid=True, is_corrected=False)

        if destination_element == "L702" or ("commoditycode" in lower and "qualifier" in lower):
            canonical = "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCodeQualifier2"
            if clean != canonical:
                return _make_result(
                    canonical, is_valid=True, is_corrected=True,
                    suggested=canonical, issue_type="spelling",
                    reason=f"Spelling '{source_val}' corrected to schema attribute '@CommodityCodeQualifier2' in Detail/LineItem/DescriptionMarksAndNumbers",
                    confidence=0.96,
                )
            return _make_result(canonical, is_valid=True, is_corrected=False)

        # Tariff Distance & Qualifier
        if "tariffdistance" in lower or ("tariff" in lower and "distance" in lower):
            if "qualifier" in lower:
                canonical = "Detail/LineItem/TariffReference/@DistanceQualifier"
            else:
                canonical = "Detail/LineItem/TariffReference/@TariffDistance"
            if clean != canonical:
                is_spelling = "tarrif" in lower or "dist" in lower and "@TariffDistance" not in clean
                return _make_result(
                    canonical, is_valid=True, is_corrected=True,
                    suggested=canonical,
                    issue_type="spelling" if is_spelling else "path_completion",
                    reason=f"Resolved to schema attribute '{canonical.split('/')[-1]}' in {canonical}",
                    confidence=0.95,
                )
            return _make_result(canonical, is_valid=True, is_corrected=False)

        # SpecialChargeOrAllowanceCode (L108)
        if destination_element == "L108" or "specialcharge" in lower:
            canonical = "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode"
            if clean != canonical:
                return _make_result(
                    canonical, is_valid=True, is_corrected=True,
                    suggested=canonical, issue_type="spelling",
                    reason=f"Resolved '{source_val}' to schema attribute '@SpecialChargeOrAllowanceCode' in Detail/LineItem/RateAndCharges",
                    confidence=0.95,
                )
            return _make_result(canonical, is_valid=True, is_corrected=False)

        # TariffServiceCode (B312)
        if destination_element == "B312" or "tariffservice" in lower or "tarifservice" in lower:
            canonical = "Header/BeginningSegmentForCarriersInvoice/@TariffServiceCode"
            if clean != canonical:
                is_spelling = "tarriff" in lower or "tarif" in lower
                return _make_result(
                    canonical, is_valid=True, is_corrected=True,
                    suggested=canonical, issue_type="spelling" if is_spelling else "path_completion",
                    reason=f"Spelling '{source_val}' corrected to schema attribute '@TariffServiceCode' in Header/BeginningSegmentForCarriersInvoice",
                    confidence=0.95,
                )
            return _make_result(canonical, is_valid=True, is_corrected=False)

        # ReferenceInformation & EDICode (N9 Header)
        if "referenceinformation" in lower or "referenceinfo" in lower or "edicode" in lower:
            if "edicode" in lower or destination_element == "N901":
                canonical = "Header/ReferenceList/ReferenceInformation/@EDICode"
            elif "qualifier" in lower or destination_element == "N903":
                canonical = "Header/ReferenceList/ReferenceInformation/@ReferenceInformationQualifier"
            else:
                canonical = "Header/ReferenceList/ReferenceInformation/@ReferenceInformation"

            if clean != canonical:
                # Check for container mismatch (e.g. Header/Currency/ReferenceInformation/@EDICode)
                if "currency" in lower:
                    return _make_result(
                        canonical, is_valid=True, is_corrected=True,
                        suggested=canonical, issue_type="container_structure",
                        reason=f"Invalid container 'Currency' in '{source_val}' corrected to canonical container 'Header/ReferenceList'",
                        confidence=1.0,
                    )
                return _make_result(
                    canonical, is_valid=True, is_corrected=True,
                    suggested=canonical, issue_type="path_completion",
                    reason=f"Canonical container 'Header/ReferenceList/' prepended to '{source_val}' per schema",
                    confidence=1.0,
                )
            return _make_result(canonical, is_valid=True, is_corrected=False)

        # ── 2. Check if clean path is already exact and valid ──
        cleaned_no_slash = clean.strip("/")
        if cleaned_no_slash in valid_paths or cleaned_no_slash in self.CANONICAL_KNOWN_PATHS.values():
            return _make_result(cleaned_no_slash, is_valid=True, is_corrected=False)

        # ── 3. Check Known Dictionary by Leaf Token ──
        # Extract leaf token (after last slash or @)
        leaf_match = re.search(r"[@/]?([A-Za-z0-9_]+)$", clean)
        leaf_token = leaf_match.group(1) if leaf_match else clean
        clean_leaf = re.sub(r"[^a-zA-Z0-9]", "", leaf_token).lower()

        # Direct leaf lookup
        if clean_leaf in leaf_map:
            canonical = leaf_map[clean_leaf]

            # Context-sensitive container selection when attribute appears in multiple segments
            seg = destination_element[:2] if len(destination_element) >= 2 else ""
            if clean_leaf in ("weightunitcode", "weight", "datetimequalifier", "date"):
                attr_name = canonical.split("/")[-1].lstrip("@")
                if seg == "B3":
                    canonical = f"Header/BeginningSegmentForCarriersInvoice/@{attr_name}"
                elif seg in ("L0", "L1", "LX"):
                    canonical = f"Detail/LineItem/LineItemQuantityAndWeight/@{attr_name}"
                elif seg in ("L3", "SE"):
                    canonical = f"Summary/TotalWeightAndCharges/@{attr_name}"
                elif seg == "G62":
                    canonical = f"Header/DateTimes/DateTime/@{attr_name}"

            if clean != canonical:
                # Check if this was just an attribute name under the correct parent container
                parent_leaf = parent_path.split("/")[-1] if parent_path else ""
                canon_parent_leaf = canonical.split("/")[-2] if len(canonical.split("/")) >= 2 else ""
                if parent_leaf and parent_leaf.lower() == canon_parent_leaf.lower() and clean_leaf == canonical.split("/")[-1].lstrip("@").lower():
                    # Exact attribute name under matching container - keep valid without correction
                    return _make_result(canonical, is_valid=True, is_corrected=False)

                is_completion = not clean.startswith(("Header/", "Detail/", "Summary/", "Invoice/"))
                return _make_result(
                    canonical,
                    is_valid=True,
                    is_corrected=True,
                    suggested=canonical,
                    issue_type="path_completion" if is_completion else "spelling",
                    reason=f"Path resolved to schema path '{canonical}'",
                    confidence=0.95,
                )
            return _make_result(canonical, is_valid=True, is_corrected=False)

        # ── 4. Fuzzy Match for Spelling Mistakes (e.g. ComodityCode, TarriffServiceCode, NetAmoutDue) ──
        candidates = list(leaf_map.keys())
        close_matches = difflib.get_close_matches(clean_leaf, candidates, n=1, cutoff=0.65)
        if close_matches:
            matched_key = close_matches[0]
            canonical = leaf_map[matched_key]
            attr_name = canonical.split("/")[-1]
            return _make_result(
                canonical,
                is_valid=True,
                is_corrected=True,
                suggested=canonical,
                issue_type="spelling",
                reason=f"Spelling '{leaf_token}' corrected to schema attribute '{attr_name}' in {canonical}",
                confidence=0.92,
            )

        # Check for container name typos (e.g. GeographicalLocation -> GeographicLocation)
        if "geograph" in lower:
            canonical = "Header/PartyList/Party/GeographicLocation/@CityName"
            if "state" in lower or destination_element == "N402":
                canonical = "Header/PartyList/Party/GeographicLocation/@StateOrProvinceCode"
            elif "postal" in lower or "zip" in lower or destination_element == "N403":
                canonical = "Header/PartyList/Party/GeographicLocation/@PostalCode"
            elif "country" in lower or destination_element == "N404":
                canonical = "Header/PartyList/Party/GeographicLocation/@CountryCode"

            return _make_result(
                canonical,
                is_valid=True,
                is_corrected=True,
                suggested=canonical,
                issue_type="spelling",
                reason=f"Spelling '{source_val}' corrected to schema element 'GeographicLocation'",
                confidence=0.90,
            )

        # ── 5. Hierarchical Fallback with Parent Context ──
        resolved = self.resolve_canonical_path(source_val, parent_path)
        if resolved and resolved != source_val:
            resolved_leaf = re.sub(r"[^a-zA-Z0-9]", "", resolved.split("/")[-1].lstrip("@")).lower()
            if (
                resolved in valid_paths
                or resolved.strip("/") in valid_paths
                or resolved in self.CANONICAL_KNOWN_PATHS.values()
                or resolved_leaf in leaf_map
            ):
                return _make_result(
                    resolved,
                    is_valid=True,
                    is_corrected=True,
                    suggested=resolved,
                    issue_type="path_completion",
                    reason=f"Resolved relative path '{source_val}' under parent '{parent_path}'",
                    confidence=0.85,
                )

        # ── 6. Fallback for Explicit Non-Path Values (Constants, Omissions, Functions) ──
        if (clean.startswith(("'", '"')) and clean.endswith(("'", '"'))) or re.match(r"^\d+(\.\d+)?$", clean) or lower in ("true", "false"):
            return _make_result(clean, is_valid=True, is_corrected=False)
        if lower in ("not mapped", "not mapped by default", "n/a", "commented out", "excluded", "omit", "none", "unknown"):
            return _make_result(clean, is_valid=True, is_corrected=False)

        # ── 7. Completely Wrong / Not in Canonical Schema ──
        # Attribute or path does not exist in Canonical Schema and cannot be resolved via spelling.
        # Treat as non-schema mapping (same as Volume): ask user to confirm whether to ignore or keep from matrix.
        xsd_name = schema_data.get("xsd_name", "InvoiceCanonicalSchema.xsd")
        elem_display = f" ({destination_element})" if destination_element else ""
        reason = (
            f"Path/Attribute '{source_val}'{elem_display} is not defined in Canonical Schema ({xsd_name}). "
            f"Confirm whether to ignore this mapping or keep it from matrix."
        )
        return _make_result(
            clean,
            is_valid=False,
            is_corrected=False,
            suggested=clean,
            issue_type="not_in_schema",
            reason=reason,
            confidence=0.95,
        )

    def resolve_canonical_path(self, source_val: str, parent_path: str = "") -> str:
        """
        Hierarchically and authoritatively resolves canonical path using:
        1. Known canonical domain dictionary
        2. Parent container context
        3. Canonical schema naming patterns
        """
        if not source_val:
            return ""

        clean = re.sub(r"\s*/\s*", "/", source_val).strip()
        lower = clean.lower()

        # ── 1. Priority canonical domain mappings (Commodity, Tariff, Freight, Non-Schema Attributes) ──
        if "volume" in lower:
            if "qualifier" in lower or "unit" in lower:
                return "Detail/LineItem/LineItemQuantityAndWeight/@VolumeUnitQualifier"
            return "Detail/LineItem/LineItemQuantityAndWeight/@Volume"

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

        # Check ReferenceInformation directly (always Header/ReferenceList)
        if "referenceinformation" in lower or "referenceinfo" in lower:
            if "qualifier" in lower or "referenceinformationqualifier" in lower:
                return "Header/ReferenceList/ReferenceInformation/@ReferenceInformationQualifier"
            if "edicode" in lower:
                return "Header/ReferenceList/ReferenceInformation/@EDICode"
            return "Header/ReferenceList/ReferenceInformation/@ReferenceInformation"

        if clean in ("ReferenceList", "Header/ReferenceList"):
            return "Header/ReferenceList"

        # Check known dictionary directly
        known = self.resolve_known_path(clean)
        if known:
            return known

        # ── 2. Extract path token ──
        path_match = re.search(r"([A-Za-z0-9_]+/[A-Za-z0-9_/@]+|@[A-Za-z0-9_]+)", clean)
        if not path_match:
            return clean

        extracted = path_match.group(1).strip()
        lower_extracted = extracted.lower()

        # Check extracted token against known dictionary
        known_token = self.resolve_known_path(extracted)
        if known_token:
            return known_token

        # Check ReferenceInformation extracted token
        if "referenceinformation" in lower_extracted:
            if "edicode" in lower_extracted:
                return "Header/ReferenceList/ReferenceInformation/@EDICode"
            if "qualifier" in lower_extracted:
                return "Header/ReferenceList/ReferenceInformation/@ReferenceInformationQualifier"
            return "Header/ReferenceList/ReferenceInformation/@ReferenceInformation"

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

        if extracted.startswith("ReferenceInformation/"):
            return f"Header/ReferenceList/{extracted}"

        if extracted.startswith("ReferenceList/"):
            return f"Header/{extracted}"

        if extracted.startswith(("BeginningSegmentForCarriersInvoice/", "Currency/", "TransactionSetheader/", "PartyList/", "EquipmentList/", "DateTimes/")):
            return f"Header/{extracted}"

        if extracted.startswith("DateTime/"):
            if any(k in lower_extracted for k in ("pickupdate", "deliverydate", "invoicedate")):
                attr = extracted.split("@")[-1]
                return f"Header/BeginningSegmentForCarriersInvoice/@{attr}"
            return f"Header/DateTimes/{extracted}"

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

    def resolve_candidates(self, xsd_path: Path, element_name: str) -> dict:
        tree = etree.parse(str(xsd_path), PARSER)
        ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
        candidates = []
        for el in tree.xpath("//xs:element[@name=$n]", namespaces=ns, n=element_name):
            ancestors = []
            cur = el
            while cur is not None:
                if etree.QName(cur).localname == "element" and cur.get("name"):
                    ancestors.append(cur.get("name"))
                cur = cur.getparent()
            candidates.append({
                "path_hint": "/" + "/".join(reversed(ancestors)),
                "type": el.get("type"),
                "minOccurs": el.get("minOccurs", "1"),
                "maxOccurs": el.get("maxOccurs", "1"),
            })
        return {
            "element": element_name,
            "status": "resolved" if len(candidates) == 1 else "ambiguous" if candidates else "not_found",
            "candidates": candidates,
        }
