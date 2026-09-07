from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from assignment import AssignmentError, decide_assignment


class AssignmentTests(unittest.TestCase):
    def call(self, **kwargs):
        return decide_assignment(frontend_account="front", backend_account="back", **kwargs)

    def test_precedence_and_visible_sources(self):
        self.assertEqual("explicit_assignee", self.call(explicit_assignee="alice", explicit_side="backend", evidence_side="frontend")["assignment_source"])
        self.assertEqual("explicit_frontend", self.call(explicit_side="frontend", evidence_side="backend")["assignment_source"])
        self.assertEqual("explicit_backend", self.call(explicit_side="backend", evidence_side="frontend")["assignment_source"])
        self.assertEqual("evidence_frontend", self.call(evidence_side="frontend")["assignment_source"])
        self.assertEqual("evidence_backend", self.call(evidence_side="backend")["assignment_source"])
        self.assertEqual({"side": "backend", "assignee": "back", "assignment_source": "default_backend"}, self.call())

    def test_missing_owner_and_invalid_explicit_assignee_fail_closed(self):
        with self.assertRaises(AssignmentError):
            decide_assignment(frontend_account="", backend_account="back")
        with self.assertRaises(AssignmentError):
            self.call(explicit_assignee=" alice")


if __name__ == "__main__":
    unittest.main()
