
from __future__ import annotations

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

from ..fake_zentao.server import FakeZenTao
from ..support import run_cli
from zentao_skill.internal.errors import ApiError
from zentao_skill.internal.zentao.feedbacks import FeedbacksAPI
from zentao_skill.internal.zentao.files import FilesAPI
from zentao_skill.internal.zentao.tickets import TicketsAPI


class SkillScenarioTests(unittest.TestCase):
    def test_non_integrated_system_sends_empty_children_array(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "system", "create", "--product", "1", "--integrated", "0",
                "--name", "scenario-system", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual([], fake.state.requests[-1]["body"]["children"])

    def test_product_plan_edit_preserves_product_and_status_fields(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "product-plan", "edit", "1", "--product", "1", "--status", "wait",
                "--title", "edited-plan", "--parent", "0", "--branch", "0",
                "--begin", "2026-08-01", "--end", "2026-08-31",
                "--desc", "plan description", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            body = fake.state.requests[-1]["body"]
            self.assertEqual(1, body["productID"])
            self.assertEqual(1, body["product"])
            self.assertEqual("wait", body["status"])

    def test_release_edit_preserves_product_fields(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "release", "edit", "1", "--product", "1", "--system", "1",
                "--name", "edited-release", "--build", "1", "--status", "wait",
                "--date", "2026-08-01", "--desc", "release description", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            body = fake.state.requests[-1]["body"]
            self.assertEqual(1, body["productID"])
            self.assertEqual(1, body["product"])

    def test_feedback_and_ticket_status_only_success_is_not_treated_as_object(self) -> None:
        for api, call in (
            (FeedbacksAPI, lambda value: value.create(product=1, title="feedback")),
            (TicketsAPI, lambda value: value.create(product=1, title="ticket")),
        ):
            with self.subTest(api=api.__name__):
                session = Mock()
                session.post.return_value = {"status": "success"}
                with self.assertRaises(ApiError):
                    call(api(session))

        for api, call in (
            (FeedbacksAPI, lambda value: value.close(item_id=1, closed_reason="commented")),
            (TicketsAPI, lambda value: value.close(item_id=1, closed_reason="commented", comment="close")),
        ):
            with self.subTest(api=f"{api.__name__}.close"):
                session = Mock()
                session.put.return_value = None
                with self.assertRaises(ApiError):
                    call(api(session))

    def test_file_write_empty_response_is_not_treated_as_success(self) -> None:
        session = Mock()
        session.post.return_value = None
        session.put.return_value = None
        session.delete.return_value = None
        with self.assertRaises(ApiError):
            FilesAPI(session).upload(file="/tmp/sample.txt", object_type="task", object_id=1)
        with self.assertRaises(ApiError):
            FilesAPI(session).edit(item_id=1, file_name="renamed.txt")
        self.assertEqual({"status": "success", "id": 1}, FilesAPI(session).delete(item_id=1))

    def test_product_crud_lifecycle_uses_explicit_commands(self) -> None:
        with FakeZenTao() as fake:
            created=run_cli(fake.base_url,["product","create","--name","scenario-product","--json"])
            self.assertEqual(0,created.returncode,created.stderr)
            ident=json.loads(created.stdout)["id"]
            self.assertEqual(0,run_cli(fake.base_url,["product","view",str(ident),"--json"]).returncode)
            self.assertEqual(0,run_cli(fake.base_url,["product","edit",str(ident),"--name","renamed","--json"]).returncode)
            self.assertEqual(0,run_cli(fake.base_url,["product","delete",str(ident),"--yes","--json"]).returncode)
            missing=run_cli(fake.base_url,["product","view",str(ident),"--json"])
            self.assertEqual(1,missing.returncode)

    def test_task_state_sequence(self) -> None:
        with FakeZenTao() as fake:
            created=run_cli(fake.base_url,["task","create","--name","scenario-task","--execution","1","--json"])
            ident=json.loads(created.stdout)["id"]
            self.assertEqual(0,run_cli(fake.base_url,["task","start",str(ident),"--real-started","2026-08-25 09:00:00","--json"]).returncode)
            self.assertEqual(0,run_cli(fake.base_url,["task","finish",str(ident),"--current-consumed","1","--real-started","2026-08-25 09:00:00","--finished-date","2026-08-25 10:00:00","--json"]).returncode)
            self.assertEqual(0,run_cli(fake.base_url,["task","close",str(ident),"--json"]).returncode)
            active=run_cli(fake.base_url,["task","activate",str(ident),"--json"])
            self.assertEqual("active",json.loads(active.stdout)["status"])
            self.assertEqual(0,run_cli(fake.base_url,["task","delete",str(ident),"--yes","--json"]).returncode)


if __name__ == "__main__": unittest.main()
