import unittest
from pathlib import Path
import sys

# Ensure backend app is in path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.python_matrix_reader import PythonMatrixReaderService
from app.services.canonical_path_resolver import CanonicalPathResolver
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

    def test_daikin_matrix_removes_unmapped_c2_and_adds_multi_n9_and_n1(self):
        daikin_path = Path("data/jobs/0422b400-f674-48ce-8830-705cdd589799/input/Daikin_America_210_Mapping_Document.docx")
        if not daikin_path.exists():
            return

        reader = PythonMatrixReaderService()
        proposal_svc = PythonXsltProposalService()
        patcher = XsltPatchService()

        spec = reader.read_matrix(daikin_path, "210")
        # Ensure N9 does not bleed Currency
        n9_paths = [m.source_canonical_path for m in spec.mappings if "N9" in m.destination_element]
        self.assertTrue(all("Currency" not in p for p in n9_paths))
        self.assertTrue(any("Header/ReferenceList/ReferenceInformation" in p for p in n9_paths))

        # Check C301 is active (not crossed out)
        c301_maps = [m for m in spec.mappings if m.destination_element == "C301"]
        self.assertTrue(any(not m.is_crossed for m in c301_maps))

        # Check proposals
        proposals = proposal_svc.generate_proposals(
            self.baseline_xslt,
            [m.model_dump() for m in spec.mappings],
            "210",
        )
        out_path = Path("data/test_daikin_unit_out.xslt")
        try:
            res = patcher.apply_proposals(self.baseline_xslt, proposals, out_path)
            content = out_path.read_text(encoding="utf-8")

            # C2 removed completely
            self.assertNotIn("<ns0:C2>", content)
            self.assertNotIn("<C201>", content)

            # C301 active
            self.assertIn("<C301>", content)

            # Both dynamic loop and static segment in N9
            self.assertIn("12</N901>", content)
            self.assertIn("DAI</N902>", content)
            self.assertIn("Header/ReferenceList/ReferenceInformation", content)

            # N1 party loops have N103 and N104
            self.assertIn("<N103>ZZ</N103>", content)
            self.assertIn("@EDICode='SF'", content)
            self.assertIn("@EDICode='ST'", content)
        finally:
            if out_path.exists():
                out_path.unlink()

    def test_schema_fuzzy_spelling_and_container_corrections(self):
        """Verifies spelling corrections, container corrections, and review points."""
        resolver = CanonicalPathResolver()

        # 1. Typo in CommodityCode -> Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2
        res1 = resolver.resolve_with_diagnostics("ComodityCode", destination_element="L707")
        self.assertTrue(res1.is_corrected)
        self.assertEqual(res1.canonical_path, "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2")
        self.assertEqual(res1.issue_type, "spelling")
        self.assertIn("@CommodityCode2", res1.reason)

        # 2. Typo in TariffServiceCode -> Header/BeginningSegmentForCarriersInvoice/@TariffServiceCode
        res2 = resolver.resolve_with_diagnostics("TarriffServiceCode", destination_element="B312")
        self.assertTrue(res2.is_corrected)
        self.assertEqual(res2.canonical_path, "Header/BeginningSegmentForCarriersInvoice/@TariffServiceCode")
        self.assertEqual(res2.issue_type, "spelling")

        # 3. Invalid container Currency for ReferenceInformation -> Header/ReferenceList/ReferenceInformation/@EDICode
        res3 = resolver.resolve_with_diagnostics("Header/Currency/ReferenceInformation/@EDICode", destination_element="N901")
        self.assertTrue(res3.is_corrected)
        self.assertEqual(res3.canonical_path, "Header/ReferenceList/ReferenceInformation/@EDICode")
        self.assertEqual(res3.issue_type, "container_structure")
        self.assertIn("Header/ReferenceList", res3.reason)

        # 4. Correct path kept as-is without flagging
        res4 = resolver.resolve_with_diagnostics(
            "Header/BeginningSegmentForCarriersInvoice/@InvoiceNumber",
            destination_element="B302",
        )
        self.assertFalse(res4.is_corrected)
        self.assertEqual(res4.canonical_path, "Header/BeginningSegmentForCarriersInvoice/@InvoiceNumber")
        self.assertEqual(res4.issue_type, "none")

        # 5. Typo in NetAmountDue (NetAmoutDue)
        res5 = resolver.resolve_with_diagnostics("NetAmoutDue", destination_element="B307")
        self.assertTrue(res5.is_corrected)
        self.assertEqual(res5.canonical_path, "Header/BeginningSegmentForCarriersInvoice/@NetAmountDue")
        self.assertEqual(res5.issue_type, "spelling")

    def test_lxloop1_product_line_item_exclusion_condition(self):
        """
        Verifies LXLoop1 condition when matrix specifies:
        'Do not product line items' / 'Populate only when special charge allowance code is not empty'.
        Checks extraction condition, proposal generation, patch application, and transform output.
        """
        from app.services.python_matrix_reader import is_lx_special_charge_filter
        
        # 1. Test helper regex
        note_text = "Do not  product line items\nPopulate only when special charge allowance code is not empty"
        self.assertTrue(is_lx_special_charge_filter(note_text))
        self.assertTrue(is_lx_special_charge_filter("where specialchargeallowncecode must not be empty only for those we need to populate the lxloop"))
        self.assertTrue(is_lx_special_charge_filter("RateAndCharges/@SpecialChargeOrAllowanceCode != ''"))
        self.assertFalse(is_lx_special_charge_filter("Standard line item without filter"))

        # 2. Test proposal generation with LX condition
        mappings_with_lx_filter = [
            {
                "mapping_id": "MAP-LX01",
                "destination_segment": "LX",
                "destination_element": "LX01",
                "source_canonical_path": "position()",
                "mapping_rule": "Position() in loop",
                "parent_segment": "LXLoop1",
                "parent_condition": "RateAndCharges/@SpecialChargeOrAllowanceCode != '' (Exclude product line items)",
                "conditions": ["RateAndCharges/@SpecialChargeOrAllowanceCode != '' (Exclude product line items)"],
                "related_notes": [note_text],
            }
        ]

        proposal_service = PythonXsltProposalService()
        proposals = proposal_service.generate_proposals(self.baseline_xslt, mappings_with_lx_filter, "210")
        
        # Verify MAP-LOOP-LXLOOP1-CONDITION proposal exists
        lx_prop = next((p for p in proposals if p["mapping_id"] == "MAP-LOOP-LXLOOP1-CONDITION"), None)
        self.assertIsNotNone(lx_prop)
        self.assertEqual(lx_prop["action"], "replace_select")
        self.assertIn("SpecialChargeOrAllowanceCode != ''", lx_prop["expression"])

        # 3. Test patch application to baseline XSLT
        patch_service = XsltPatchService()
        out_path = self.project_root / "backend" / "data" / "test_lx_patched_210.xslt"
        try:
            res = patch_service.apply_proposals(self.baseline_xslt, proposals, out_path)
            self.assertTrue(out_path.exists())
            content = out_path.read_text(encoding="utf-8")
            self.assertIn("Detail/LineItemList/LineItem[RateAndCharges/@SpecialChargeOrAllowanceCode != '']", content)

            # 4. Transform test XML: Line items 1 & 2 (charges) included, line item 3 (product) excluded
            patched_tree = etree.parse(str(out_path))
            transform = etree.XSLT(patched_tree)
            test_doc = etree.parse(str(self.canonical_xml))
            result_doc = transform(test_doc)
            result_str = str(result_doc)

            # Only 2 LXLoop1 segments generated
            out_xml = etree.fromstring(bytes(result_doc))
            lx_loops = out_xml.xpath("//*[local-name()='LXLoop1']")
            self.assertEqual(len(lx_loops), 2)

            # Loop 1 = Fuel Surcharge, Loop 2 = Line Haul
            l502_nodes = out_xml.xpath("//*[local-name()='LXLoop1']//*[local-name()='L502']")
            self.assertEqual(len(l502_nodes), 2)
            self.assertIn("Fuel Surcharge", l502_nodes[0].text)
            self.assertIn("Line Haul", l502_nodes[1].text)
        finally:
            if out_path.exists():
                out_path.unlink()


if __name__ == "__main__":
    unittest.main()

