import unittest
from pathlib import Path
from app.services.xslt_patch_service import XsltPatchService
from app.services.python_xslt_proposal_service import PythonXsltProposalService
from app.services.canonical_path_resolver import CanonicalPathResolver

class TestL0VolumePatch(unittest.TestCase):
    def test_canonical_path_resolver_volume_diagnostics(self):
        resolver = CanonicalPathResolver()
        diag_vol = resolver.resolve_with_diagnostics("Map @Volume from LineItemQuantityAndWeight", destination_element="L006")
        self.assertEqual(diag_vol.canonical_path, "Detail/LineItem/LineItemQuantityAndWeight/@Volume")
        self.assertEqual(diag_vol.issue_type, "not_in_schema")
        self.assertFalse(diag_vol.is_valid)
        self.assertIn("not defined in Canonical Schema", diag_vol.reason)

        diag_qual = resolver.resolve_with_diagnostics("@VolumeUnitQualifier", destination_element="L007")
        self.assertEqual(diag_qual.canonical_path, "Detail/LineItem/LineItemQuantityAndWeight/@VolumeUnitQualifier")
        self.assertEqual(diag_qual.issue_type, "not_in_schema")
        self.assertFalse(diag_qual.is_valid)

    def test_arbitrary_non_schema_paths_diagnostics(self):
        resolver = CanonicalPathResolver()
        # Non-existent attribute under LineItemQuantityAndWeight
        diag1 = resolver.resolve_with_diagnostics("Detail/LineItem/LineItemQuantityAndWeight/@NonExistentAttr", destination_element="L009")
        self.assertEqual(diag1.issue_type, "not_in_schema")
        self.assertFalse(diag1.is_valid)
        self.assertIn("not defined in Canonical Schema", diag1.reason)

        # Invalid container and field
        diag2 = resolver.resolve_with_diagnostics("Header/InvalidContainer/@FakeField", destination_element="B302")
        self.assertEqual(diag2.issue_type, "not_in_schema")
        self.assertFalse(diag2.is_valid)
        self.assertIn("not defined in Canonical Schema", diag2.reason)

        # Valid paths should remain valid
        diag_valid = resolver.resolve_with_diagnostics("Detail/LineItem/LineItemQuantityAndWeight/@Weight", destination_element="L008")
        self.assertTrue(diag_valid.is_valid)
        self.assertEqual(diag_valid.issue_type, "none")

        # Spelling mistakes should still be corrected
        diag_spelling = resolver.resolve_with_diagnostics("ComodityCode", destination_element="L707")
        self.assertTrue(diag_spelling.is_valid)
        self.assertEqual(diag_spelling.issue_type, "spelling")
        self.assertEqual(diag_spelling.suggested_path, "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2")

    def test_proposal_service_volume_kept_generates_l006_and_l007(self):
        baseline = Path("backend/data/references/210/standard_xslt")
        mappings = [
            {
                "mapping_id": "MAP-L006",
                "destination_element": "L006",
                "destination_segment": "L0",
                "source_canonical_path": "Detail/LineItem/LineItemQuantityAndWeight/@Volume",
                "loop_relative_path": "LineItemQuantityAndWeight/@Volume",
                "is_crossed": False,
                "is_constant": False,
            },
            {
                "mapping_id": "MAP-L007",
                "destination_element": "L007",
                "destination_segment": "L0",
                "source_canonical_path": "Detail/LineItem/LineItemQuantityAndWeight/@VolumeUnitQualifier",
                "loop_relative_path": "LineItemQuantityAndWeight/@VolumeUnitQualifier",
                "is_crossed": False,
                "is_constant": False,
            }
        ]
        proposals = PythonXsltProposalService().generate_proposals(baseline, mappings, "210")
        vol_p = next((p for p in proposals if p["mapping_id"] == "MAP-L0-VOLUME"), None)
        self.assertIsNotNone(vol_p)
        self.assertEqual(vol_p["action"], "replace_node")
        self.assertIn("<L006>", vol_p["expression"])
        self.assertIn("<L007>", vol_p["expression"])

        # Patch and verify
        out = Path("backend/tests/fixtures/test_vol_kept.xslt")
        try:
            res = XsltPatchService().apply_proposals(baseline, proposals, out)
            self.assertGreater(len(res["applied"]), 0)
            content = out.read_text(encoding="utf-8")
            self.assertIn("<L006>", content)
            self.assertIn("<L007>", content)
            self.assertIn("LineItemQuantityAndWeight/@Volume", content)
            self.assertIn("LineItemQuantityAndWeight/@VolumeUnitQualifier", content)
        finally:
            if out.exists():
                out.unlink()

    def test_proposal_service_volume_ignored_omits_l006_and_l007(self):
        baseline = Path("backend/data/references/210/standard_xslt")
        # User confirmed to ignore / omit
        mappings = [
            {
                "mapping_id": "MAP-L006",
                "destination_element": "L006",
                "destination_segment": "L0",
                "source_canonical_path": "Detail/LineItem/LineItemQuantityAndWeight/@Volume",
                "loop_relative_path": "LineItemQuantityAndWeight/@Volume",
                "is_crossed": True,  # Ignored by user!
                "is_constant": False,
            },
            {
                "mapping_id": "MAP-L007",
                "destination_element": "L007",
                "destination_segment": "L0",
                "source_canonical_path": "Detail/LineItem/LineItemQuantityAndWeight/@VolumeUnitQualifier",
                "loop_relative_path": "LineItemQuantityAndWeight/@VolumeUnitQualifier",
                "is_crossed": True,  # Ignored by user!
                "is_constant": False,
            }
        ]
        proposals = PythonXsltProposalService().generate_proposals(baseline, mappings, "210")
        vol_p = next((p for p in proposals if p["mapping_id"] == "MAP-L0-VOLUME"), None)
        self.assertIsNone(vol_p)

        # Patch and verify neither L006 nor L007 appears in generated XSLT
        out = Path("backend/tests/fixtures/test_vol_ignored.xslt")
        try:
            res = XsltPatchService().apply_proposals(baseline, proposals, out)
            content = out.read_text(encoding="utf-8")
            self.assertNotIn("<L006>", content)
            self.assertNotIn("<L007>", content)
        finally:
            if out.exists():
                out.unlink()

if __name__ == "__main__":
    unittest.main()
