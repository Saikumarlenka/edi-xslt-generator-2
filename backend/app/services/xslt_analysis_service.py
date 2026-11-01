from pathlib import Path
import re
from lxml import etree

PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, recover=False, huge_tree=False)

def parse_xml_file(path: Path):
    """Parse XML safely, correcting a known text-file encoding declaration mismatch.

    Some supplied BizTalk .xsl maps declare UTF-16 but are actually single-byte text.
    If the file has no UTF-16 NUL-byte pattern, normalize only that declaration in
    memory so the map can be inspected; generated output is written as UTF-8.
    """
    data = Path(path).read_bytes()
    head = data[:200]
    if b"\x00" not in head and re.search(br'encoding\s*=\s*["\']utf-16["\']', head, re.I):
        data = re.sub(br'encoding\s*=\s*(["\'])utf-16\1', b'encoding="UTF-8"', data, count=1, flags=re.I)
    root = etree.fromstring(data, PARSER)
    return etree.ElementTree(root)

class XsltAnalysisService:
    def analyze(self, path: Path) -> dict:
        tree = parse_xml_file(path)
        root = tree.getroot()
        if not root.tag.endswith("stylesheet") and not root.tag.endswith("transform"):
            raise ValueError("Selected standard map root is not an XSLT stylesheet/transform")
        ns = {"xsl": "http://www.w3.org/1999/XSL/Transform"}
        templates = [{"match": t.get("match"), "name": t.get("name"), "mode": t.get("mode")} for t in root.xpath("//xsl:template", namespaces=ns)]
        paths = sorted({(e.get("select") or e.get("test") or "").strip() for e in root.iter() if e.get("select") or e.get("test")})
        helper_templates = []
        for node in root.xpath("//xsl:template[@name]", namespaces=ns):
            helper_templates.append({"name": node.get("name"), "parameters": [p.get("name") for p in node.xpath("./xsl:param", namespaces=ns)], "body_excerpt": "".join(node.itertext()).strip()[:1200]})
        extension_calls = sorted({token for path_expr in paths for token in __import__("re").findall(r"([A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*)\s*\(", path_expr)})
        null_guarded = sum(1 for node in root.xpath("//xsl:value-of[@select]", namespaces=ns) if any(etree.QName(a).namespace == ns["xsl"] and etree.QName(a).localname in {"if", "when"} for a in node.iterancestors()))
        value_of_count = len(root.xpath("//xsl:value-of[@select]", namespaces=ns))
        return {"version": root.get("version", "unknown"), "namespaces": dict(root.nsmap), "templates": templates, "helper_templates": helper_templates, "extension_calls": extension_calls, "null_guard_audit": {"value_of_count": value_of_count, "guarded_count": null_guarded}, "expressions": paths, "segment_order": self._literal_elements(root)}

    def _literal_elements(self, root):
        xsl_ns = "http://www.w3.org/1999/XSL/Transform"
        return [etree.QName(e).localname for e in root.iter() if isinstance(e.tag, str) and etree.QName(e).namespace != xsl_ns and etree.QName(e).localname not in {"stylesheet", "transform"}][:500]
