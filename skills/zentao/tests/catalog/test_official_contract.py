from __future__ import annotations

import copy
import unittest

from ..support import CATALOG
from ..contract.official_oracle import (
    OFFICIAL_ENDPOINTS,
    assert_catalog_matches_official,
    official_entry_count,
    specific_source_count,
)


class OfficialContractEvidenceTest(unittest.TestCase):
    def test_independent_snapshot_is_complete_and_sources_are_explicit(self) -> None:
        self.assertEqual(120, official_entry_count())
        self.assertEqual(120, len(OFFICIAL_ENDPOINTS))
        self.assertEqual({item["endpoint_id"] for item in CATALOG}, set(OFFICIAL_ENDPOINTS))
        self.assertGreater(specific_source_count(), 0)
        for item in OFFICIAL_ENDPOINTS.values():
            self.assertIn(item["source_status"], {"specific", "index_reference"})
            self.assertEqual("2026-08-25", item.get("official_doc_last_checked"), item["endpoint_id"])
            if item["source_status"] == "index_reference":
                self.assertTrue(item.get("source_note"), item["endpoint_id"])

    def test_runtime_catalog_matches_static_official_evidence(self) -> None:
        for item in CATALOG:
            with self.subTest(endpoint=item["endpoint_id"]):
                assert_catalog_matches_official(item)

    def test_mutations_are_rejected_by_independent_oracle(self) -> None:
        by_id = {item["endpoint_id"]: item for item in CATALOG}

        bad_build = copy.deepcopy(by_id["bug.resolve"])
        build = next(p for p in bad_build["parameters"]["body"] if p["api_name"] == "resolvedBuild")
        build["type"] = "integer"
        with self.assertRaises(AssertionError):
            assert_catalog_matches_official(bad_build)

        bad_browse = copy.deepcopy(by_id["bug.list_product"])
        browse = next(p for p in bad_browse["parameters"]["query"] if p["api_name"] == "browseType")
        browse["enum_map"].pop("assigned-to-me")
        with self.assertRaises(AssertionError):
            assert_catalog_matches_official(bad_browse)

        bad_relation = copy.deepcopy(by_id["user.edit"])
        dept = next(p for p in bad_relation["parameters"]["body"] if p["api_name"] == "dept")
        dept["minimum"] = 1
        with self.assertRaises(AssertionError):
            assert_catalog_matches_official(bad_relation)


if __name__ == "__main__":
    unittest.main()
