from pathlib import Path
from lxml import etree
from app.services.xslt_analysis_service import PARSER

class CanonicalPathResolver:
    """Conservative schema lookup. It validates element-name presence, not semantic intent by itself."""

    CANONICAL_KNOWN_PATHS = {
        "commoditycode2": "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2",
        "commoditycodequalifier2": "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCodeQualifier2",
        "commoditycode": "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode",
        "commoditycodequalifier": "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCodeQualifier",
        "tariffdistance": "Detail/LineItem/TariffReference/@TariffDistance",
        "distancequalifier": "Detail/LineItem/TariffReference/@DistanceQualifier",
        "tariffsection": "Detail/LineItem/TariffReference/@TariffSection",
        "freightclasscode": "Detail/LineItem/TariffReference/@FreightClassCode",
        "specialchargeorallowancecode": "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode",
        "freightrate": "Detail/LineItem/RateAndCharges/@FreightRate",
        "ratevaluequalifier": "Detail/LineItem/RateAndCharges/@RateValueQualifier",
        "charge": "Detail/LineItem/RateAndCharges/@Charge",
        "totalcharges": "Summary/TotalWeightAndCharges/@TotalCharges",
    }

    def resolve_known_path(self, field_name: str) -> str | None:
        """Resolves authoritative canonical path for known domain attributes."""
        clean = (field_name or "").strip().lstrip("@").lower()
        return self.CANONICAL_KNOWN_PATHS.get(clean)

    def resolve_candidates(self, xsd_path: Path, element_name: str) -> dict:
        tree = etree.parse(str(xsd_path), PARSER)
        ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
        candidates=[]
        for el in tree.xpath("//xs:element[@name=$n]", namespaces=ns, n=element_name):
            ancestors=[]
            cur=el
            while cur is not None:
                if etree.QName(cur).localname == "element" and cur.get("name"):
                    ancestors.append(cur.get("name"))
                cur=cur.getparent()
            candidates.append({"path_hint":"/" + "/".join(reversed(ancestors)),"type":el.get("type"),"minOccurs":el.get("minOccurs","1"),"maxOccurs":el.get("maxOccurs","1")})
        return {"element":element_name,"status":"resolved" if len(candidates)==1 else "ambiguous" if candidates else "not_found","candidates":candidates}
