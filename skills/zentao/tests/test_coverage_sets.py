from __future__ import annotations

import unittest

from .contract.test_all_endpoints import CONTRACT_ENDPOINT_IDS
from .e2e.test_all_cli_endpoints import E2E_ENDPOINT_IDS
from .fake_zentao.router import FAKE_ENDPOINT_IDS
from .support import CATALOG, internal_endpoint_ids, skill_route_endpoint_ids
from zentao_skill.cli.main import CLI_ENDPOINT_IDS


class CoverageSetTests(unittest.TestCase):
    def test_all_coverage_sets_match_the_catalog(self) -> None:
        catalog=frozenset(item["endpoint_id"] for item in CATALOG)
        self.assertEqual(120,len(catalog))
        self.assertEqual(catalog,internal_endpoint_ids())
        self.assertEqual(catalog,CLI_ENDPOINT_IDS)
        self.assertEqual(catalog,skill_route_endpoint_ids())
        self.assertEqual(catalog,FAKE_ENDPOINT_IDS)
        self.assertEqual(catalog,CONTRACT_ENDPOINT_IDS)
        self.assertEqual(catalog,E2E_ENDPOINT_IDS)


if __name__ == "__main__": unittest.main()
