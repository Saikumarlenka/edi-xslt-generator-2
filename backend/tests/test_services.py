from pathlib import Path
import tempfile
import unittest
from lxml import etree
from app.services.canonical_path_resolver import CanonicalPathResolver
from app.services.xslt_patch_service import XsltPatchService
from app.services.validation_service import XsltValidationService

class TestServices(unittest.TestCase):
    def test_canonical_path_resolver(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            xsd=tmp_path/"s.xsd"
            xsd.write_text('''<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"><xs:element name="Root"><xs:complexType><xs:sequence><xs:element name="Shipment" type="xs:string"/></xs:sequence></xs:complexType></xs:element></xs:schema>''',encoding="utf-8")
            result=CanonicalPathResolver().resolve_candidates(xsd,"Shipment")
            self.assertEqual(result["status"], "resolved")
            self.assertEqual(result["candidates"][0]["path_hint"], "/Root/Shipment")

    def test_patch_service_does_not_rewrite_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            base=tmp_path/"base.xslt"; out=tmp_path/"out.xslt"
            original='''<?xml version="1.0"?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="/"><out/></xsl:template></xsl:stylesheet>'''
            base.write_text(original,encoding="utf-8")
            XsltPatchService().apply_proposals(base,[{"mapping_id":"M1","action":"propose_change","target_xpath":"//xsl:template","expression":"bad"}],out)
            self.assertIn("<out", out.read_text(encoding="utf-8"))

    def test_validation_well_formed(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            p=tmp_path/"a.xslt"; p.write_text('''<?xml version="1.0"?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="/"><out/></xsl:template></xsl:stylesheet>''',encoding="utf-8")
            result=XsltValidationService().validate(p)
            self.assertEqual(result["items"][0]["status"], "passed")

    def test_safe_patch_replaces_only_existing_select_and_preserves_segment_order(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            base = tmp_path / "base.xslt"
            out = tmp_path / "out.xslt"
            base.write_text('''<?xml version="1.0"?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="/"><out><A><xsl:value-of select="OldPath"/></A><B/></out></xsl:template></xsl:stylesheet>''', encoding="utf-8")
            result = XsltPatchService().apply_proposals(base, [{"mapping_id":"M1","action":"replace_select","target_xpath":"//xsl:value-of[@select='OldPath']","expression":"NewPath"}], out)
            self.assertEqual(result["applied_count"], 1)
            tree = etree.parse(str(out))
            self.assertEqual(tree.xpath("string(//xsl:value-of/@select)", namespaces={"xsl":"http://www.w3.org/1999/XSL/Transform"}), "NewPath")
            self.assertEqual([etree.QName(n).localname for n in tree.xpath("//*[local-name()='A' or local-name()='B']")], ["A", "B"])

    def test_safe_patch_refuses_ambiguous_target(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            base = tmp_path / "base.xslt"
            out = tmp_path / "out.xslt"
            base.write_text('''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="/"><out><xsl:value-of select="A"/><xsl:value-of select="A"/></out></xsl:template></xsl:stylesheet>''', encoding="utf-8")
            result = XsltPatchService().apply_proposals(base, [{"mapping_id":"M1","action":"replace_select","target_xpath":"//xsl:value-of","expression":"B"}], out)
            self.assertEqual(result["applied_count"], 0)
            self.assertTrue(result["unresolved"])

    def test_x12_structure_check_detects_bad_se01(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            xslt = tmp_path / "bad-count.xslt"
            xslt.write_text('''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="/"><X12_00401_210><ST><ST01>210</ST01><ST02>1</ST02></ST><B3/><SE><SE01>99</SE01><SE02>1</SE02></SE></X12_00401_210></xsl:template></xsl:stylesheet>''', encoding="utf-8")
            source = tmp_path / "source.xml"
            source.write_text("<root/>", encoding="utf-8")
            result = XsltValidationService().validate(xslt, source, transaction="210")
            check = next(x for x in result["items"] if x["name"] == "X12 SE01 segment count")
            self.assertEqual(check["status"], "warning")

if __name__ == "__main__":
    unittest.main()
