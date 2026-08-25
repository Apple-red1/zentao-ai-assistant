
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
    def test_program_create_rejects_blank_name_before_http(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "program", "create", "--name", "", "--begin", "2027-01-01",
                "--end", "2027-12-31", "--json",
            ])
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertEqual("USAGE_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], fake.state.requests)

    def test_product_description_is_sent_as_scalar_text(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "product", "create", "--name", "description-product",
                "--desc", "面向企业客户的统一 CRM", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("面向企业客户的统一 CRM", fake.state.requests[-1]["body"]["desc"])

    def test_product_create_rejects_blank_name_before_http(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "product", "create", "--name", "", "--json",
            ])
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertEqual("USAGE_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], fake.state.requests)

    def test_bug_edit_rejects_unsupported_assignment_argument(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "bug", "edit", "1", "--assignee", "admin", "--json",
            ])
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertEqual([], fake.state.requests)

    def test_bug_create_sends_21_7_8_product_compatibility_alias(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "bug", "create", "--product", "1", "--title", "product-alias",
                "--affected-build", "trunk", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            body = fake.state.requests[-1]["body"]
            self.assertEqual(1, body["productID"])
            self.assertEqual(1, body["product"])

    def test_epic_duplicate_close_sends_duplicate_story(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "epic", "close", "1", "--closed-reason", "duplicate",
                "--duplicate-story", "2", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            body = fake.state.requests[-1]["body"]
            self.assertEqual("duplicate", body["closedReason"])
            self.assertEqual(2, body["duplicateStory"])

    def test_requirement_duplicate_close_sends_duplicate_story(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "requirement", "close", "1", "--closed-reason", "duplicate",
                "--duplicate-story", "2", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            body = fake.state.requests[-1]["body"]
            self.assertEqual("duplicate", body["closedReason"])
            self.assertEqual(2, body["duplicateStory"])

    def test_test_case_defaults_step_types_for_multistep_requests(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "test-case", "create", "--product", "1", "--title", "multi-step",
                "--step", "one", "--step", "two", "--expect", "first", "--expect", "second",
                "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(["step", "step"], fake.state.requests[-1]["body"]["stepType"])

    def test_requirement_edit_requires_reviewers_before_http(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "requirement", "edit", "1", "--title", "edited-requirement", "--priority", "1", "--json",
            ])
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertEqual("USAGE_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], fake.state.requests)

    def test_epic_edit_can_preserve_reviewers_when_target_requires_them(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "epic", "edit", "1", "--title", "edited-epic",
                "--priority", "1", "--estimate", "0.5", "--reviewer", "admin", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(["admin"], fake.state.requests[-1]["body"]["reviewer"])

    def test_epic_edit_requires_reviewers_before_http(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "epic", "edit", "1", "--title", "edited-epic", "--priority", "1", "--json",
            ])
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stdout)
            self.assertEqual("USAGE_ERROR", json.loads(result.stderr)["error"]["code"])
            self.assertEqual([], fake.state.requests)

    def test_enum_mapping_is_field_scoped_and_preserves_free_text_and_credentials(self) -> None:
        with FakeZenTao() as fake:
            result = run_cli(fake.base_url, [
                "bug", "create", "--product", "1", "--title", "code-error",
                "--affected-build", "trunk", "--type", "code-error",
                "--steps", "design-defect", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            body = fake.state.requests[-1]["body"]
            self.assertEqual("code-error", body["title"])
            self.assertEqual("codeerror", body["type"])
            self.assertEqual("design-defect", body["steps"])

            result = run_cli(fake.base_url, [
                "user", "create", "--account", "enum-account", "--realname", "agile-plus",
                "--password", "code-error", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            body = fake.state.requests[-1]["body"]
            self.assertEqual("agile-plus", body["realname"])
            self.assertEqual("code-error", body["password"])

            result = run_cli(fake.base_url, [
                "project", "create", "--name", "enum-project", "--model", "waterfall-plus",
                "--begin", "2026-08-25", "--end", "2026-08-26", "--json",
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("waterfallplus", fake.state.requests[-1]["body"]["model"])

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
        with self.assertRaises(ApiError):
            FilesAPI(session).delete(item_id=1)

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
