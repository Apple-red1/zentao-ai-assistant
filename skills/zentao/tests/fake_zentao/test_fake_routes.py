from __future__ import annotations

import copy
import re
import unittest

from ..support import CATALOG
from .router import ALL_ROUTES, FAKE_ENDPOINT_IDS
from .server import FakeZenTao
from .state import FakeState
from zentao_skill.internal.errors import HttpFailure
from zentao_skill.internal.http.client import HttpClient


class FakeRouteTests(unittest.TestCase):
    def test_all_120_routes_are_explicit(self) -> None:
        expected={item["endpoint_id"] for item in CATALOG}
        self.assertEqual(expected, FAKE_ENDPOINT_IDS)
        self.assertEqual(120, len(ALL_ROUTES))
        for route in ALL_ROUTES:
            concrete=re.sub(r"\{[^}]+\}", "1", route.path)
            self.assertIsNotNone(route.regex.fullmatch(concrete), route.endpoint_id)

    def test_state_reset_is_deterministic(self) -> None:
        state=FakeState(); first=copy.deepcopy(state.resources)
        state.resources["bug"].pop("1")
        state.reset()
        self.assertEqual(first, state.resources)

    def test_fake_rejects_missing_required_fields_and_invalid_enums(self) -> None:
        with FakeZenTao() as fake:
            http=HttpClient(timeout=1)
            login=http.request("POST", fake.base_url + "/api.php/v2/users/login", json_body={"account":"admin","password":"secret"})
            token=login["token"]
            with self.assertRaises(HttpFailure) as missing:
                http.request("POST", fake.base_url + "/api.php/v2/bugs", headers={"Token":token}, json_body={"title":"missing product/build"})
            self.assertEqual(400, missing.exception.status)
            with self.assertRaises(HttpFailure) as invalid:
                http.request("PUT", fake.base_url + "/api.php/v2/bugs/1/resolve", headers={"Token":token}, json_body={"resolution":"invalid"})
            self.assertEqual(400, invalid.exception.status)

    def test_fake_exposes_all_required_fault_types_without_fake_api_endpoints(self) -> None:
        state=FakeState()
        faults=("401","403","404","422","500","502","503","timeout","malformed_json","drop","commit_then_drop")
        state.plan_faults("bug.view", *faults)
        self.assertEqual(list(faults), state.faults["bug.view"])
        self.assertFalse(any("/test/" in route.path for route in ALL_ROUTES))


if __name__ == "__main__": unittest.main()
