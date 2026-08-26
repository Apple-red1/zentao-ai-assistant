from __future__ import annotations

import json
import unittest
from collections import Counter

from ..support import CATALOG, SKILL_ROOT


EVIDENCE = json.loads(
    (SKILL_ROOT / "references" / "compatibility" / "zentao-21.7.8.json").read_text(encoding="utf-8")
)


class CompatibilityEvidenceTest(unittest.TestCase):
    def test_evidence_statuses_and_catalog_are_one_to_one(self) -> None:
        catalog = {item["endpoint_id"]: item for item in CATALOG}
        statuses: dict[str, str] = {}
        for record in EVIDENCE["observations"]:
            self.assertIn(record["status"], {"observed", "unsupported"})
            self.assertTrue(record.get("observed_at"), record)
            self.assertTrue(record.get("evidence_id"), record)
            self.assertTrue(record.get("notes"), record)
            for endpoint_id in record["endpoint_ids"]:
                self.assertIn(endpoint_id, catalog)
                self.assertNotIn(endpoint_id, statuses, endpoint_id)
                statuses[endpoint_id] = record["status"]

        for endpoint_id, status in statuses.items():
            self.assertEqual(status, catalog[endpoint_id]["compatibility"], endpoint_id)
        for endpoint_id, item in catalog.items():
            if endpoint_id not in statuses:
                self.assertEqual("not_observed", item["compatibility"], endpoint_id)

        counts = Counter(item["compatibility"] for item in CATALOG)
        self.assertEqual(dict(counts), EVIDENCE["status_counts"])
        self.assertEqual(len(CATALOG), EVIDENCE["endpoint_count"])

    def test_unsupported_is_distinct_from_missing_observation(self) -> None:
        statuses = {endpoint_id: record["status"] for record in EVIDENCE["observations"] for endpoint_id in record["endpoint_ids"]}
        self.assertTrue(any(status == "unsupported" for status in statuses.values()))
        self.assertTrue(any(status == "observed" for status in statuses.values()))
        self.assertTrue(any(item["compatibility"] == "not_observed" for item in CATALOG if item["endpoint_id"] not in statuses))


if __name__ == "__main__":
    unittest.main()
