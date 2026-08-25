from __future__ import annotations

import unittest

from ..fake_zentao.server import FakeZenTao
from zentao_skill.internal.config import Config
from zentao_skill.internal.errors import ApiError, MalformedResponse, NetworkError, UnknownWriteResult
from zentao_skill.internal.http.client import HttpClient
from zentao_skill.internal.zentao.bugs import BugsAPI
from zentao_skill.internal.zentao.session import ZentaoSession


class ErrorSemanticsTests(unittest.TestCase):
    def session(self, fake: FakeZenTao, timeout: float = 1) -> ZentaoSession:
        return ZentaoSession(Config(fake.base_url, "admin", "secret"), http=HttpClient(timeout=timeout), retry_delays=(0, 0))

    def calls(self, fake: FakeZenTao, endpoint_id: str) -> list[dict[str, object]]:
        return [request for request in fake.state.requests if request["endpoint_id"] == endpoint_id]

    def test_get_retries_transient_http_failures_then_succeeds(self) -> None:
        for status in ("502", "503", "504"):
            with self.subTest(status=status), FakeZenTao() as fake:
                fake.state.plan_faults("bug.view", status, status)
                result = BugsAPI(self.session(fake)).view(item_id=1)
                self.assertEqual(1, result["id"])
                self.assertEqual(3, len(self.calls(fake, "bug.view")))

    def test_get_stops_after_three_transient_http_failures(self) -> None:
        for status in ("502", "503", "504"):
            with self.subTest(status=status), FakeZenTao() as fake:
                fake.state.plan_faults("bug.view", status, status, status)
                with self.assertRaises(ApiError):
                    BugsAPI(self.session(fake)).view(item_id=1)
                self.assertEqual(3, len(self.calls(fake, "bug.view")))

    def test_get_does_not_retry_non_transient_http_failures(self) -> None:
        for status in ("400", "401", "403", "404", "422", "500"):
            with self.subTest(status=status), FakeZenTao() as fake:
                fake.state.plan_faults("bug.view", status)
                with self.assertRaises(ApiError):
                    BugsAPI(self.session(fake)).view(item_id=1)
                self.assertEqual(1, len(self.calls(fake, "bug.view")))

    def test_get_retries_response_drop_and_fails_after_three_drops(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.view", "drop", "drop")
            self.assertEqual(1, BugsAPI(self.session(fake)).view(item_id=1)["id"])
            self.assertEqual(3, len(self.calls(fake, "bug.view")))
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.view", "drop", "drop", "drop")
            with self.assertRaises(NetworkError):
                BugsAPI(self.session(fake)).view(item_id=1)
            self.assertEqual(3, len(self.calls(fake, "bug.view")))

    def test_get_retries_timeout_and_fails_after_three_timeouts(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.view", "timeout", "timeout", "timeout")
            with self.assertRaises(NetworkError):
                BugsAPI(self.session(fake, timeout=0.05)).view(item_id=1)
            self.assertEqual(3, len(self.calls(fake, "bug.view")))

    def test_malformed_json_is_protocol_error_not_retry(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.view", "malformed_json")
            with self.assertRaises(MalformedResponse):
                BugsAPI(self.session(fake)).view(item_id=1)
            self.assertEqual(1, len(self.calls(fake, "bug.view")))

    def test_explicit_write_http_failures_are_api_errors_without_retry(self) -> None:
        for status in ("400", "401", "403", "404", "422", "500", "502", "503", "504"):
            with self.subTest(status=status), FakeZenTao() as fake:
                fake.state.plan_faults("bug.edit", status)
                with self.assertRaises(ApiError):
                    BugsAPI(self.session(fake)).edit(item_id=1, title="changed")
                self.assertEqual(1, len(self.calls(fake, "bug.edit")))
                self.assertEqual(1, len([r for r in fake.state.requests if r["endpoint_id"] != "token.login"]))

    def test_post_put_delete_transport_uncertainty_never_retries(self) -> None:
        operations = (
            ("bug.create", lambda api: api.create(product=1, title="new", affected_build=[1])),
            ("bug.edit", lambda api: api.edit(item_id=1, title="changed")),
            ("bug.delete", lambda api: api.delete(item_id=1)),
        )
        for endpoint_id, operation in operations:
            with self.subTest(endpoint=endpoint_id), FakeZenTao() as fake:
                fake.state.plan_faults(endpoint_id, "drop")
                with self.assertRaises(UnknownWriteResult):
                    operation(BugsAPI(self.session(fake)))
                self.assertEqual(1, len(self.calls(fake, endpoint_id)))
                self.assertEqual(1, len([r for r in fake.state.requests if r["endpoint_id"] != "token.login"]))

    def test_write_timeout_is_unknown_and_never_retried(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.edit", "timeout")
            with self.assertRaises(UnknownWriteResult):
                BugsAPI(self.session(fake, timeout=0.05)).edit(item_id=1, title="changed")
            self.assertEqual(1, len(self.calls(fake, "bug.edit")))

    def test_write_commit_then_drop_is_unknown_and_never_retried_or_queried(self) -> None:
        with FakeZenTao() as fake:
            fake.state.plan_faults("bug.edit", "commit_then_drop")
            with self.assertRaises(UnknownWriteResult):
                BugsAPI(self.session(fake)).edit(item_id=1, title="changed")
            self.assertEqual(1, len(self.calls(fake, "bug.edit")))
            self.assertEqual("changed", fake.state.resources["bug"]["1"]["title"])
            self.assertFalse(any(r["endpoint_id"] == "bug.view" for r in fake.state.requests))
            self.assertEqual(1, len([r for r in fake.state.requests if r["endpoint_id"] != "token.login"]))

    def test_write_definitely_not_sent_is_network_error(self) -> None:
        fake = FakeZenTao()
        fake.__enter__()
        try:
            session = self.session(fake, timeout=0.1)
            session.ensure_login()
            fake.__exit__(None, None, None)
            with self.assertRaises(NetworkError):
                BugsAPI(session).edit(item_id=1, title="changed")
        finally:
            if fake.thread.is_alive():
                fake.__exit__(None, None, None)

    def test_connection_refused_login_is_network_error(self) -> None:
        session=ZentaoSession(Config("http://127.0.0.1:9","admin","secret"),http=HttpClient(timeout=0.1),retry_delays=(0,0))
        with self.assertRaises(NetworkError):
            session.ensure_login()


if __name__ == "__main__": unittest.main()
