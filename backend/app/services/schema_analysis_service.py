from pathlib import Path
from lxml import etree
from app.services.xslt_analysis_service import PARSER

class SchemaAnalysisService:
    def analyze(self, path: Path) -> dict:
        tree = etree.parse(str(path), PARSER)
        root = tree.getroot()
        ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
        elements = []
        for el in root.xpath("//xs:element", namespaces=ns):
            elements.append({"name": el.get("name"), "ref": el.get("ref"), "type": el.get("type"), "minOccurs": el.get("minOccurs", "1"), "maxOccurs": el.get("maxOccurs", "1")})
        return {"target_namespace": root.get("targetNamespace"), "element_count": len(elements), "elements": elements}

    def validate_xml(self, xsd_path: Path, xml_path: Path) -> list[str]:
        schema_doc = etree.parse(str(xsd_path), PARSER)
        schema = etree.XMLSchema(schema_doc)
        xml_doc = etree.parse(str(xml_path), PARSER)
        if schema.validate(xml_doc): return []
        return [str(e) for e in schema.error_log]
