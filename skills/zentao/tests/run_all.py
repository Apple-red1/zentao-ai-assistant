from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO_ROOT=ROOT.parents[1]
SCRIPTS=ROOT/"scripts"
for value in (str(REPO_ROOT), str(ROOT), str(SCRIPTS)):
    if value not in sys.path: sys.path.insert(0,value)


def coverage_summary() -> tuple[list[tuple[str, frozenset[str], frozenset[str]]], bool]:
    from tests.contract.test_all_endpoints import CONTRACT_ENDPOINT_IDS
    from tests.e2e.test_all_cli_endpoints import E2E_ENDPOINT_IDS
    from tests.fake_zentao.router import FAKE_ENDPOINT_IDS
    from tests.support import CATALOG, internal_endpoint_ids, skill_route_endpoint_ids
    from zentao_skill.cli.main import CLI_ENDPOINT_IDS

    catalog=frozenset(item["endpoint_id"] for item in CATALOG)
    surfaces=[
        ("Catalog",catalog,catalog),
        ("Internal",frozenset(internal_endpoint_ids()),catalog),
        ("CLI",frozenset(CLI_ENDPOINT_IDS),catalog),
        ("Skill routes",frozenset(skill_route_endpoint_ids()),catalog),
        ("Fake API",frozenset(FAKE_ENDPOINT_IDS),catalog),
        ("Contract tests",frozenset(CONTRACT_ENDPOINT_IDS),catalog),
        ("CLI E2E",frozenset(E2E_ENDPOINT_IDS),catalog),
    ]
    exact = len(catalog) == 120 and all(actual == expected for _,actual,expected in surfaces)
    return surfaces, exact


def main() -> int:
    suite=unittest.defaultTestLoader.discover(str(ROOT/"tests"),pattern="test_*.py",top_level_dir=str(ROOT))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    surfaces, exact=coverage_summary()
    from tests.contract.official_oracle import (
        OFFICIAL_ENDPOINTS,
        assert_catalog_matches_official,
        specific_source_count,
    )
    from tests.support import CATALOG, SKILL_ROOT

    official_match = 0
    for item in CATALOG:
        try:
            assert_catalog_matches_official(item)
        except AssertionError:
            continue
        official_match += 1
    status="PASS" if result.wasSuccessful() and exact else "FAIL"
    print("\nZenTao API v2 coverage\n")
    for label,actual,expected in surfaces:
        print(f"{label + ':':<18}{len(actual):>3} / {len(expected)}")
        missing=sorted(expected-actual)
        extra=sorted(actual-expected)
        if missing:
            print(f"  missing: {', '.join(missing)}")
        if extra:
            print(f"  extra:   {', '.join(extra)}")
    print(f"Official snapshot:  {official_match:>3} / {len(OFFICIAL_ENDPOINTS)}")
    print(f"Specific sources:   {specific_source_count():>3} / {len(OFFICIAL_ENDPOINTS)}")
    compatibility = json.loads(
        (SKILL_ROOT / "references" / "compatibility" / "zentao-21.7.8.json").read_text(encoding="utf-8")
    )
    compatibility_counts = Counter(item["compatibility"] for item in CATALOG)
    print(f"21.7.8 observed:    {compatibility_counts['observed']:>3} / {len(CATALOG)}")
    print(f"21.7.8 unsupported: {compatibility_counts['unsupported']:>3} / {len(CATALOG)}")
    print(f"21.7.8 not observed: {compatibility_counts['not_observed']:>3} / {len(CATALOG)}")
    if dict(compatibility_counts) != compatibility["status_counts"]:
        status = "FAIL"
    print("\nReal API calls:      0")
    print(f"Result: {status}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
