import unittest
from pathlib import Path
import sys

# Ensure backend app is in path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.python_matrix_reader import PythonMatrixReaderService
from app.services.python_xslt_proposal_service import PythonXsltProposalService
from app.services.xslt_patch_service import XsltPatchService
from app.services.validation_service import XsltValidationService
from app.services.xslt_analysis_service import parse_xml_file
from lxml import etree


class TestPythonMatrixReaderAndProposals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = backend_dir.parent
        cls.docx_path = cls.project_root / "reference-files" / "210" / "210_mapping_matrix_Sonoco_RXO.docx"
        cls.baseline_xslt = cls.project_root / "reference-files" / "210" / "210_standard_base.xsl"
        cls.canonical_xml = cls.project_root / "reference-files" / "210" / "210_canonical_test.xml"
        cls.edi_xsd = cls.project_root / "reference-files" / "210" / "X12_00401_210.xsd"
        cls.canonical_xsd = cls.project_root / "reference-files" / "210" / "InvoiceCanonicalSchema.xsd"

    def test_python_matrix_extraction(self):
        reader = PythonMatrixReaderService()
        spec = reader.read_matrix(self.docx_path, "210")

        self.assertEqual(spec.transaction, "210")
        self.assertEqual(spec.extraction_method, "python")
        self.assertGreater(len(spec.mappings), 80)

        # Check crossed out detection
        crossed = [m for m in spec.mappings if m.is_crossed]
        self.assertGreater(len(crossed), 10)
        # B301 is strikethrough in Sonoco RXO docx
        b301 = next((m for m in spec.mappings if m.destination_element == "B301"), None)
        self.assertIsNotNone(b301)
        self.assertTrue(b301.is_crossed)
        self.assertEqual(b301.implementation_status, "excluded_crossed_out")

        # Check constants detection
        constants = [m for m in spec.mappings if m.is_constant]
        self.assertGreater(len(constants), 10)
        # C201 is hardcoded to "R"
        c201 = next((m for m in spec.mappings if m.destination_element == "C201"), None)
        self.assertIsNotNone(c201)
        self.assertTrue(c201.is_constant)
        self.assertIn("R", c201.constants)

        # Check hierarchical path resolution
        b302 = next((m for m in spec.mappings if m.destination_element == "B302"), None)
        self.assertIsNotNone(b302)
        self.assertEqual(b302.destination_segment, "B3")
        self.assertIn("BeginningSegmentForCarriersInvoice/@InvoiceNumber", b302.source_canonical_path)

        # Check condition inheritance
        n901 = next((m for m in spec.mappings if m.destination_element == "N901"), None)
        self.assertIsNotNone(n901)
        self.assertTrue(any("ReferenceInformation/@EDICode" in c for c in n901.conditions))

        # Check L108 is NOT crossed out and has full canonical path
        l108 = next((m for m in spec.mappings if m.destination_element == "L108"), None)
        self.assertIsNotNone(l108)
        self.assertFalse(l108.is_crossed, "L108 must not be marked as crossed-out")
        self.assertEqual(l108.source_canonical_path, "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode")

        # Check L7 / Commodity Code 2 has authoritative canonical path
        l707 = next((m for m in spec.mappings if m.destination_element == "L707"), None)
        self.assertIsNotNone(l707)
        self.assertEqual(l707.source_canonical_path, "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2")
        self.assertTrue(any("commoditycode2" in c.lower() for c in l707.conditions))

        # Check TariffDistance and DistanceQualifier path resolutions
        self.assertEqual(
            reader._resolve_canonical_path("TariffDistance", "Detail/LineItem/TariffReference"),
            "Detail/LineItem/TariffReference/@TariffDistance",
        )
        self.assertEqual(
            reader._resolve_canonical_path("@TariffDistance", ""),
            "Detail/LineItem/TariffReference/@TariffDistance",
        )
        self.assertEqual(
            reader._resolve_canonical_path("@DistanceQualifier", ""),
            "Detail/LineItem/TariffReference/@DistanceQualifier",
        )

    def test_proposal_generation_and_patching(self):
        reader = PythonMatrixReaderService()
        spec = reader.read_matrix(self.docx_path, "210")

        proposal_service = PythonXsltProposalService()
        proposals = proposal_service.generate_proposals(
            self.baseline_xslt,
            [m.model_dump() for m in spec.mappings],
            "210",
        )
        self.assertGreater(len(proposals), 15)

        # Ensure crossed-out elements like B301 or B308 are commented out in XSLT based on matrix
        b301_prop = next((p for p in proposals if p["mapping_id"] == "MAP-B301"), None)
        if b301_prop:
            self.assertEqual(b301_prop["action"], "comment_out")

        # Ensure L108 has conditional node replacement or omit test replacement
        l108_prop = next((p for p in proposals if p["mapping_id"] == "MAP-L108"), None)
        self.assertIsNotNone(l108_prop)
        self.assertIn(l108_prop["action"], ("replace_node", "replace_test"))
        self.assertIn("SpecialChargeOrAllowanceCode", l108_prop["expression"])

        out_path = backend_dir / "data" / "unit_test_output.xslt"
        try:
            patch_result = XsltPatchService().apply_proposals(self.baseline_xslt, proposals, out_path)
            self.assertGreater(patch_result["applied_count"], 10)
            self.assertEqual(len(patch_result["unresolved"]), 0)

            # Validate compiled XSLT
            val = XsltValidationService().validate(
                out_path,
                self.canonical_xml,
                self.edi_xsd,
                self.canonical_xsd,
                self.baseline_xslt,
                "210",
            )
            # Compilation & XML well-formedness must pass
            xml_item = next(it for it in val["items"] if it["name"] == "XSLT XML well-formedness")
            self.assertEqual(xml_item["status"], "passed")
            xslt_comp = next(it for it in val["items"] if it["name"] == "XSLT compilation")
            self.assertEqual(xslt_comp["status"], "passed")
            seq_item = next(it for it in val["items"] if it["name"] == "Baseline segment sequence")
            self.assertIn(seq_item["status"], ("passed", "warning"))
        finally:
            if out_path.exists():
                out_path.unlink()

    def test_gemini_spec_enrichment_canonical_paths_and_not_crossed(self):
        from app.models.mapping import MappingRecord, MappingSpecification
        from app.services.gemini_matrix_reader import GeminiMatrixReaderService

        service = GeminiMatrixReaderService()
        spec = MappingSpecification(
            transaction="210",
            mappings=[
                MappingRecord(
                    mapping_id="MAP-L108",
                    destination_element="L108",
                    destination_segment="L1",
                    source_document_reference="L108",
                    source_description="Special Charge Code",
                    mapping_rule="IF @SpecialChargeOrAllowanceCode = 'LHS' THEN omit element IF @SpecialChargeorAllowanceCode = '405' THEN send 'FUE'",
                    source_canonical_path="@SpecialChargeOrAllowanceCode",
                ),
                MappingRecord(
                    mapping_id="MAP-L707",
                    destination_element="L707",
                    destination_segment="L7",
                    source_document_reference="L707",
                    source_description="Commodity Code",
                    mapping_rule="@Commoditycode2 (first available)",
                    source_canonical_path="@Commoditycode2",
                ),
                MappingRecord(
                    mapping_id="MAP-TARIFF",
                    destination_element="L703",
                    destination_segment="L7",
                    source_document_reference="Tariff",
                    source_description="Distance",
                    mapping_rule="Tariff Distance in miles",
                    source_canonical_path="@TariffDistance",
                ),
            ]
        )
        service._enrich_spec(spec)

        m_l108 = next(m for m in spec.mappings if m.destination_element == "L108")
        self.assertFalse(m_l108.is_crossed, "L108 must not be marked is_crossed in Gemini enrichment")
        self.assertEqual(m_l108.source_canonical_path, "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode")

        m_l707 = next(m for m in spec.mappings if m.destination_element == "L707")
        self.assertEqual(m_l707.source_canonical_path, "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2")

        m_tariff = next(m for m in spec.mappings if m.destination_element == "L703")
        self.assertEqual(m_tariff.source_canonical_path, "Detail/LineItem/TariffReference/@TariffDistance")

    def test_end_to_end_xslt_matches_production_rules(self):
        spec = PythonMatrixReaderService().read_matrix(self.docx_path, "210")
        proposals = PythonXsltProposalService().generate_proposals(
            self.baseline_xslt,
            [m.model_dump() for m in spec.mappings],
            "210",
        )
        out_path = backend_dir / "data" / "production_rules_test.xslt"
        try:
            patch_res = XsltPatchService().apply_proposals(self.baseline_xslt, proposals, out_path)
            self.assertEqual(len(patch_res["unresolved"]), 0)

            content = out_path.read_text(encoding="utf-8")
            # 1. Zero C# scripts or extension functions
            self.assertNotIn("<msxsl:script", content)
            self.assertNotIn("userCSharp:", content)
            self.assertNotIn("var:v", content)

            # 2. Standard top variables and output
            self.assertIn("vLowercaseChars_CONST", content)
            self.assertIn("vUppercaseChars_CONST", content)
            self.assertIn('omit-xml-declaration="yes"', content)

            # 3. Standard templates present
            self.assertIn('name="CleanAlphaField"', content)
            self.assertIn('name="SetDefaultIfEmpty"', content)
            self.assertIn('name="StopTypeMapValue"', content)

            # 4. Crossed-out elements commented out as XML comments
            self.assertIn("<!--", content)
            self.assertIn("B301", content)
            self.assertIn("B308", content)
            self.assertIn("S5Loop1", content)

            # 5. Transform produces valid XML
            gen_tree = parse_xml_file(out_path)
            gen_xslt = etree.XSLT(gen_tree)
            canonical_doc = parse_xml_file(self.canonical_xml)
            output_xml = str(gen_xslt(canonical_doc))
            self.assertIn("<B302>30011-1</B302>", output_xml)
            self.assertIn("<B304>PP</B304>", output_xml)
            self.assertIn("<N901>BM</N901>", output_xml)
            self.assertIn("<N902>TFP00001232</N902>", output_xml)
            self.assertIn("<N901>PO</N901>", output_xml)
            self.assertIn("<N902>EDI204ECHS</N902>", output_xml)
            self.assertIn("<C201>R</C201>", output_xml)
            self.assertIn("<C202>25</C202>", output_xml)
            self.assertIn("<C203>TFP-001</C203>", output_xml)
            self.assertIn("<L108>FUE</L108>", output_xml)

            # 6. Strict B304 dynamic mapping
            self.assertIn("ShipmentMethodOfPayment", content)
            self.assertNotIn("<B304>PP</B304>", content)

            # 7. Strict N9 qualifier filter without LoadType or translations
            self.assertNotIn("var:LoadType", content)
            self.assertIn("(@EDICode='BM' or @EDICode='PO')", content)

            # 8. Clean XML comments: no injected namespaces, no boilerplate text, clean relative paths
            self.assertNotIn("Segment R3 is not active", content)
            self.assertNotIn("local-name()='Invoice'", content)
            self.assertIn("Header/BeginningSegmentForCarriersInvoice/@InvoiceNumber", content)

            # Suppressed/crossed-out elements not emitted
            self.assertNotIn("<B301>", output_xml)
            self.assertNotIn("<B308>", output_xml)
            self.assertNotIn("<S5", output_xml)
            self.assertNotIn("<L7", output_xml)
        finally:
            if out_path.exists():
                out_path.unlink()


if __name__ == "__main__":
    unittest.main()

