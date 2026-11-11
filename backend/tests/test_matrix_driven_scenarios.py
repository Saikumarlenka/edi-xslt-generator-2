import unittest
from pathlib import Path
from lxml import etree

from app.services.canonical_path_resolver import CanonicalPathResolver
from app.services.python_xslt_proposal_service import PythonXsltProposalService
from app.services.xslt_patch_service import XsltPatchService
from app.services.xslt_analysis_service import parse_xml_file

class TestMatrixDrivenScenarios(unittest.TestCase):
    """
    Validates that:
    1. CanonicalPathResolver suggests paths taking parent/for-each loops into account.
    2. Changing values in the matrix directly updates the generated XSLT without hardcoded client assumptions.
    3. Custom matrix rules (party qualifiers, dates, static N9, code translations) are strictly followed.
    """

    def setUp(self):
        self.resolver = CanonicalPathResolver()
        self.proposal_service = PythonXsltProposalService()
        self.patch_service = XsltPatchService()
        self.baseline_xslt = Path(__file__).resolve().parents[2] / "reference-files" / "210" / "210_standard_base.xsl"

    def test_canonical_path_suggestions_with_parent_and_foreach_loop_context(self):
        """
        Verify that misspelled or malformed paths produce suggestions containing
        both canonical schema path and the context-relative XPath inside enclosing loops.
        """
        # Case 1: LineItem loop typo
        res = self.resolver.resolve_with_diagnostics(
            source_val="RateAndCharge/@SpecialChargeCode",
            parent_path="Detail/LineItem",
            destination_element="L108",
        )
        self.assertTrue(res.is_corrected)
        self.assertEqual(res.canonical_path, "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode")
        self.assertEqual(res.loop_context, "Detail/LineItemList/LineItem")
        self.assertEqual(res.loop_relative_path, "RateAndCharges/@SpecialChargeOrAllowanceCode")
        self.assertIn("Detail/LineItemList/LineItem", res.reason)

        # Case 2: Commodity code spelling mistake under LineItem
        res2 = self.resolver.resolve_with_diagnostics(
            source_val="comoditycode2",
            parent_path="Detail/LineItem",
            destination_element="L707",
        )
        self.assertTrue(res2.is_corrected)
        self.assertEqual(res2.canonical_path, "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2")
        self.assertEqual(res2.loop_context, "Detail/LineItemList/LineItem")
        self.assertEqual(res2.loop_relative_path, "DescriptionMarksAndNumbers/@CommodityCode2")

        # Case 3: N9 Header invalid container (Header/Currency/ReferenceInformation/@EDICode)
        res3 = self.resolver.resolve_with_diagnostics(
            source_val="Header/Currency/ReferenceInformation/@EDICode",
            parent_path="Header",
            destination_element="N901",
        )
        self.assertTrue(res3.is_corrected)
        self.assertEqual(res3.canonical_path, "Header/ReferenceList/ReferenceInformation/@EDICode")
        self.assertEqual(res3.loop_context, "Header/ReferenceList/ReferenceInformation")
        self.assertEqual(res3.loop_relative_path, "@EDICode")

        # Case 4: Party loop typo (GeographicalLocation/@City)
        res4 = self.resolver.resolve_with_diagnostics(
            source_val="GeographicalLocation/@City",
            parent_path="Header/PartyList/Party",
            destination_element="N401",
        )
        self.assertTrue(res4.is_corrected)
        self.assertEqual(res4.canonical_path, "Header/PartyList/Party/GeographicLocation/@CityName")
        self.assertEqual(res4.loop_context, "Header/PartyList/Party")
        self.assertEqual(res4.loop_relative_path, "GeographicLocation/@CityName")

    def test_matrix_value_changes_propagate_to_xslt(self):
        """
        Verify that changing values in matrix mappings (e.g., B304, G6201, N101, static N9)
        strictly updates the generated XSLT accordingly.
        """
        custom_mappings = [
            # 1. B304 changed to 'CC' (Collect) instead of standard 'PP'
            {
                "mapping_id": "MAP-B304",
                "destination_segment": "B3",
                "destination_element": "B304",
                "is_constant": True,
                "constants": ["CC"],
                "is_crossed": False,
            },
            # 2. G6201 changed to '10' (Shipment Date) instead of standard '86'
            {
                "mapping_id": "MAP-G6201",
                "destination_segment": "G62",
                "destination_element": "G6201",
                "is_constant": True,
                "constants": ["10"],
                "mapping_rule": "Hardcoded '10' for pickup",
                "is_crossed": False,
            },
            # 3. N101 for SH party changed to 'SH' instead of default 'SF'
            {
                "mapping_id": "MAP-N101-SH",
                "destination_segment": "N1",
                "destination_element": "N101",
                "parent_condition": "Where Name/@EntityIdentifierCode = 'SH'",
                "is_constant": True,
                "constants": ["SH"],
                "is_crossed": False,
            },
            # 4. Static N9 with custom values PO / 999888
            {
                "mapping_id": "MAP-N901-STATIC",
                "destination_segment": "N9",
                "destination_element": "N901",
                "is_constant": True,
                "constants": ["PO"],
                "is_crossed": False,
            },
            {
                "mapping_id": "MAP-N902-STATIC",
                "destination_segment": "N9",
                "destination_element": "N902",
                "is_constant": True,
                "constants": ["999888"],
                "is_crossed": False,
            },
            # 5. L108 with custom code translation 400 -> MSC (NOT Sonoco 405 -> FUE)
            {
                "mapping_id": "MAP-L108",
                "destination_segment": "L1",
                "destination_element": "L108",
                "mapping_rule": "when SpecialChargeOrAllowanceCode = '400' translate to 'MSC'",
                "is_crossed": False,
            },
        ]

        proposals = self.proposal_service.generate_proposals(
            baseline_path=self.baseline_xslt,
            mappings=custom_mappings,
            transaction="210",
        )

        out_xslt_path = Path("scratch/test_matrix_scenario_output.xslt")
        out_xslt_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            res = self.patch_service.apply_proposals(
                baseline_path=self.baseline_xslt,
                proposals=proposals,
                output_path=out_xslt_path,
            )
            self.assertGreater(res["applied_count"], 0)
            generated_content = out_xslt_path.read_text(encoding="utf-8")

            # Verify B304 reflects 'CC'
            self.assertIn("<B304>CC</B304>", generated_content)

            # Verify G6201 reflects '10'
            self.assertIn("<G6201>10</G6201>", generated_content)

            # Verify N101 for SH reflects 'SH' (not 'SF')
            self.assertIn("<N101>SH</N101>", generated_content)

            # Verify Static N9 reflects 'PO' and '999888'
            self.assertIn("<N901>PO</N901>", generated_content)
            self.assertIn("<N902>999888</N902>", generated_content)

            # Verify L108 reflects '400' -> 'MSC' (and does not contain Sonoco's hardcoded FUE)
            self.assertIn("'400'", generated_content)
            self.assertIn("<L108>MSC</L108>", generated_content)
            self.assertNotIn("FUE", generated_content)

        finally:
            if out_xslt_path.exists():
                out_xslt_path.unlink()

    def test_daikin_l108_omission_without_else_copy(self):
        """
        Verify Daikin L108 rule 'IF @SpecialChargeOrAllowanceCode = 'LHS' THEN omit element ELSE @SpecialChargeOrAllowanceCode':
        1. Must NOT generate <xsl:choose> with 'Else' or 'Copy'.
        2. Must generate <xsl:if test="... != '' and ... != 'LHS'"><L108>...
        """
        mappings = [
            {
                "mapping_id": "MAP-L108",
                "destination_element": "L108",
                "destination_segment": "L1",
                "mapping_rule": "IF @SpecialChargeOrAllowanceCode = 'LHS' THEN omit element ELSE @SpecialChargeOrAllowanceCode",
                "source_canonical_path": "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode",
                "is_crossed": False,
                "is_constant": False,
                "transformations": [],
                "related_notes": [],
            }
        ]
        proposals = self.proposal_service.generate_proposals(self.baseline_xslt, mappings, "210")
        l108_p = next(p for p in proposals if p["mapping_id"] == "MAP-L108")
        self.assertEqual(l108_p["action"], "replace_test")
        self.assertEqual(
            l108_p["expression"],
            "RateAndCharges/@SpecialChargeOrAllowanceCode != '' and RateAndCharges/@SpecialChargeOrAllowanceCode != 'LHS'"
        )

        # Apply patch and verify resulting XSLT
        out_xslt_path = Path("backend/tests/fixtures/test_daikin_l108.xslt")
        try:
            res = self.patch_service.apply_proposals(self.baseline_xslt, proposals, out_xslt_path)
            content = out_xslt_path.read_text(encoding="utf-8")
            self.assertNotIn("Else", content)
            self.assertNotIn("<L108>Copy</L108>", content)
            self.assertIn("RateAndCharges/@SpecialChargeOrAllowanceCode != 'LHS'", content)
            self.assertIn("<L108>", content)
        finally:
            if out_xslt_path.exists():
                out_xslt_path.unlink()

    def test_sonoco_l108_translations_without_else_copy(self):
        """
        Verify Sonoco L108 translations 405 -> FUE with LHS omission:
        1. Must NOT contain 'Else' or 'Copy'.
        2. Must translate 405 to FUE.
        3. Must omit LHS.
        """
        mappings = [
            {
                "mapping_id": "MAP-L108",
                "destination_element": "L108",
                "destination_segment": "L1",
                "mapping_rule": "IF @SpecialChargeOrAllowanceCode = 'LHS' THEN omit element IF @SpecialChargeorAllowanceCode = '405' THEN send 'FUE'ELSE @SpecialChargeOrAllowanceCode",
                "source_canonical_path": "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode",
                "is_crossed": False,
                "is_constant": False,
                "transformations": ["code_map_405_to_FUE"],
                "related_notes": ["Table updated below"],
            }
        ]
        proposals = self.proposal_service.generate_proposals(self.baseline_xslt, mappings, "210")
        l108_p = next(p for p in proposals if p["mapping_id"] == "MAP-L108")
        self.assertEqual(l108_p["action"], "replace_node")
        self.assertNotIn("Else", l108_p["expression"])
        self.assertNotIn("Copy", l108_p["expression"])
        self.assertIn("<L108>FUE</L108>", l108_p["expression"])
        self.assertIn("!= 'LHS'", l108_p["expression"])

if __name__ == "__main__":
    unittest.main()
