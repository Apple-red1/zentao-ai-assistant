from __future__ import annotations

import json
import tempfile
import unittest
from html import escape
from pathlib import Path
from unittest.mock import Mock

from zentao_skill.internal.errors import UnknownWriteResult, UsageError
from zentao_skill.internal.http.legacy import LegacyPageFailure, LegacyPageResponse
from zentao_skill.internal.zentao.comments import (
    CommentAPI,
    is_allowed,
    parse_inline_upload_response,
    parse_page_snapshot,
    snapshot_from_detail,
)
from zentao_skill.services.comments.service import CommentService


def snapshot(actions: list[dict[str, object]], *, critical: dict[str, object] | None = None) -> dict[str, object]:
    return {"actions": actions, "critical_fields": critical or {"status": "active", "title": "title"}}


def action(
    action_id: int,
    *,
    resource: str = "bug",
    object_id: int = 7,
    body: str = "hello",
    files: list[dict[str, object]] | None = None,
    account: str | None = "admin",
) -> dict[str, object]:
    value: dict[str, object] = {
        "id": action_id,
        "action": "commented",
        "objectType": resource,
        "objectID": object_id,
        "comment": body,
    }
    if files is not None:
        value["files"] = files
    if account is not None:
        value["actor"] = account
    return value


class CommentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = Mock()
        self.service = CommentService(self.api, account="admin")

    def test_capability_matrix_matches_issue_51(self) -> None:
        expected = {
            "bug": {"comment", "attachments", "inline_image"},
            "story": {"comment", "attachments", "inline_image"},
            "product": {"comment", "attachments", "inline_image"},
            "task": {"comment", "attachments", "inline_image"},
            "execution": {"comment", "attachments", "inline_image"},
            "project": {"comment", "attachments", "inline_image"},
            "test-task": {"comment", "attachments", "inline_image"},
            "product-plan": {"comment", "attachments", "inline_image"},
            "release": {"comment", "attachments", "inline_image"},
            "build": {"comment", "attachments", "inline_image"},
        }
        for resource, capabilities in expected.items():
            for capability in ("comment", "attachments", "inline_image"):
                with self.subTest(resource=resource, capability=capability):
                    self.assertEqual(capability in capabilities, is_allowed(resource, capability))

    def test_unsupported_capability_is_rejected_before_any_network_call(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / "attachment.txt"
            file_path.write_bytes(b"attachment")
            with self.assertRaises(UsageError):
                self.service.add(resource="program", object_id=7, comment="hello", files=(file_path,))
        self.api.snapshot.assert_not_called()
        self.api.get_comment_form.assert_not_called()
        self.api.post_comment.assert_not_called()

    def test_unique_new_action_is_confirmed_by_identity_and_body(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([action(10, body="old")]),
            snapshot([action(10, body="old"), action(11)]),
        ]
        self.api.get_comment_form.return_value = "uid-1"

        result = self.service.add(resource="bug", object_id=7, comment="hello")

        self.assertEqual("success", result["status"])
        self.assertEqual(11, result["action_id"])
        self.assertEqual(1, self.api.post_comment.call_count)
        self.assertEqual("hello", self.api.post_comment.call_args.kwargs["actioncomment"])

    def test_plain_comment_text_is_escaped_before_page_write(self) -> None:
        raw = '[BT-HTML-TEXT] <angle> & ampersand "quoted"'
        self.api.snapshot.side_effect = [snapshot([]), snapshot([action(11, body=escape(raw, quote=False))])]
        self.api.get_comment_form.return_value = "uid-1"

        result = self.service.add(resource="bug", object_id=7, comment=raw)

        self.assertEqual(11, result["action_id"])
        self.assertEqual(escape(raw, quote=False), self.api.post_comment.call_args.kwargs["actioncomment"])

    def test_multiple_inline_images_upload_in_order_and_share_one_comment(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([]),
            snapshot([action(11, body='hello<p><img src="/one.png"></p><p><img src="/two.png"></p>')]),
        ]
        self.api.get_comment_form.return_value = "uid-1"
        self.api.upload_inline_image.side_effect = [
            LegacyPageResponse(200, "http://localhost/upload", "application/json", b'{"fileID":21,"url":"/one.png"}'),
            LegacyPageResponse(200, "http://localhost/upload", "application/json", b'{"fileID":22,"url":"/two.png"}'),
        ]
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "one.png"
            second = Path(td) / "two.png"
            first.write_bytes(b"one")
            second.write_bytes(b"two")
            result = self.service.add(resource="bug", object_id=7, comment="hello", inline_images=(first, second))

        self.assertEqual(11, result["action_id"])
        self.assertEqual([21, 22], result["inline_file_ids"])
        self.assertEqual(2, self.api.upload_inline_image.call_count)
        self.assertEqual(
            'hello<p><img src="/one.png"></p><p><img src="/two.png"></p>',
            self.api.post_comment.call_args.kwargs["actioncomment"],
        )

    def test_repeated_inline_image_reuses_one_remote_identity_and_two_references(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([]),
            snapshot([action(11, body='hello<p><img src="/same.png"></p><p><img src="/same.png"></p>')]),
        ]
        self.api.get_comment_form.return_value = "uid-1"
        self.api.upload_inline_image.return_value = LegacyPageResponse(
            200, "http://localhost/upload", "application/json", b'{"fileID":21,"url":"/same.png"}'
        )
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "same.png"
            image.write_bytes(b"same")
            result = self.service.add(resource="bug", object_id=7, comment="hello", inline_images=(image, image))

        self.assertEqual(11, result["action_id"])
        self.assertEqual([21, 21], result["inline_file_ids"])
        self.assertEqual(1, self.api.upload_inline_image.call_count)
        self.assertEqual(2, self.api.post_comment.call_args.kwargs["actioncomment"].count("/same.png"))

    def test_story_can_use_repeatable_inline_images(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([]),
            snapshot([action(11, resource="story", body='hello<p><img src="/one.png"></p><p><img src="/two.png"></p>')]),
        ]
        self.api.get_comment_form.return_value = "uid-1"
        self.api.upload_inline_image.side_effect = [
            LegacyPageResponse(200, "http://localhost/upload", "application/json", b'{"fileID":21,"url":"/one.png"}'),
            LegacyPageResponse(200, "http://localhost/upload", "application/json", b'{"fileID":22,"url":"/two.png"}'),
        ]
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "one.png"
            second = Path(td) / "two.png"
            first.write_bytes(b"one")
            second.write_bytes(b"two")
            result = self.service.add(resource="story", object_id=7, comment="hello", inline_images=(first, second))

        self.assertEqual(11, result["action_id"])
        self.assertEqual([21, 22], result["inline_file_ids"])
        self.assertEqual(2, self.api.upload_inline_image.call_count)

    def test_files_and_inline_images_share_one_comment(self) -> None:
        files = [{"id": 31, "objectType": "comment", "objectID": 11, "name": "attachment.txt", "size": 10}]
        self.api.snapshot.side_effect = [
            snapshot([]),
            snapshot([action(11, body='hello<p><img src="/image.png"></p>', files=files)]),
        ]
        self.api.get_comment_form.return_value = "uid-1"
        self.api.upload_inline_image.return_value = LegacyPageResponse(
            200, "http://localhost/upload", "application/json", b'{"fileID":21,"url":"/image.png"}'
        )
        with tempfile.TemporaryDirectory() as td:
            attachment = Path(td) / "attachment.txt"
            image = Path(td) / "image.png"
            attachment.write_bytes(b"attachment")
            image.write_bytes(b"image")
            result = self.service.add(
                resource="bug",
                object_id=7,
                comment="hello",
                files=(attachment,),
                inline_images=(image,),
            )

        self.assertEqual(11, result["action_id"])
        self.assertEqual([31], result["file_ids"])
        self.assertEqual(21, result["inline_file_id"])
        self.assertEqual((attachment,), self.api.post_comment.call_args.kwargs["files"])
        self.assertEqual('hello<p><img src="/image.png"></p>', self.api.post_comment.call_args.kwargs["actioncomment"])

    def test_no_candidate_returns_unknown_without_replaying_post(self) -> None:
        self.api.snapshot.side_effect = [snapshot([action(10, body="old")]), snapshot([action(10, body="old")])]
        self.api.get_comment_form.return_value = "uid-1"

        with self.assertRaises(UnknownWriteResult) as raised:
            self.service.add(resource="bug", object_id=7, comment="hello")

        self.assertEqual("UNKNOWN_WRITE_RESULT", raised.exception.code)
        self.assertEqual(1, self.api.post_comment.call_count)
        self.assertEqual(2, self.api.snapshot.call_count)

    def test_multiple_same_body_candidates_are_unknown(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([action(10, body="old")]),
            snapshot([action(10, body="old"), action(11), action(12)]),
        ]
        self.api.get_comment_form.return_value = "uid-1"

        with self.assertRaises(UnknownWriteResult):
            self.service.add(resource="bug", object_id=7, comment="hello")
        self.assertEqual(1, self.api.post_comment.call_count)

    def test_attachment_identity_must_belong_to_candidate_comment_action(self) -> None:
        files = [
            {"id": 31, "objectType": "comment", "objectID": 11, "name": "a.txt", "size": 3},
            {"id": 32, "objectType": "comment", "objectID": 11, "name": "b.txt", "size": 4},
        ]
        self.api.snapshot.side_effect = [
            snapshot([]),
            snapshot([action(11, files=files)]),
        ]
        self.api.get_comment_form.return_value = "uid-1"
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "a.txt"
            second = Path(td) / "b.txt"
            first.write_bytes(b"one")
            second.write_bytes(b"two2")
            result = self.service.add(resource="bug", object_id=7, comment="hello", files=(first, second))

        self.assertEqual(11, result["action_id"])
        self.assertEqual([31, 32], result["file_ids"])

    def test_same_body_concurrent_action_is_not_accepted_when_post_action_is_missing(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([action(10, body="hello")]),
            snapshot([action(10, body="hello"), action(11, body="hello"), action(12, body="hello")]),
        ]
        self.api.get_comment_form.return_value = "uid-1"
        with self.assertRaises(UnknownWriteResult):
            self.service.add(resource="bug", object_id=7, comment="hello")

    def test_different_concurrent_action_does_not_block_unique_candidate(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([action(10, body="old")]),
            snapshot([action(10, body="old"), action(11, body="hello"), action(12, body="other")]),
        ]
        self.api.get_comment_form.return_value = "uid-1"

        result = self.service.add(resource="bug", object_id=7, comment="hello")

        self.assertEqual(11, result["action_id"])
        self.assertEqual(1, self.api.post_comment.call_count)

    def test_unknown_post_can_be_confirmed_by_one_readback_candidate(self) -> None:
        self.api.snapshot.side_effect = [snapshot([]), snapshot([action(11)])]
        self.api.get_comment_form.return_value = "uid-1"
        self.api.post_comment.side_effect = LegacyPageFailure(
            "connection lost", stage="comment", transport_uncertain=True
        )

        result = self.service.add(resource="bug", object_id=7, comment="hello")

        self.assertEqual(11, result["action_id"])
        self.assertEqual(1, self.api.post_comment.call_count)

    def test_critical_field_changes_are_reported_without_a_second_write(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([], critical={"status": "active", "title": "before"}),
            snapshot([action(11)], critical={"status": "active", "title": "after"}),
        ]
        self.api.get_comment_form.return_value = "uid-1"

        result = self.service.add(resource="bug", object_id=7, comment="hello")

        self.assertEqual({"title": {"before": "before", "after": "after"}}, result["concurrent_changes"])
        self.assertEqual(1, self.api.post_comment.call_count)

    def test_inline_upload_unknown_stops_before_comment_and_marks_possible_orphan(self) -> None:
        self.api.snapshot.return_value = snapshot([])
        self.api.get_comment_form.return_value = "uid-1"
        self.api.upload_inline_image.side_effect = LegacyPageFailure(
            "connection lost", stage="inline_upload", transport_uncertain=True
        )
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "image.png"
            image.write_bytes(b"png")
            with self.assertRaises(UnknownWriteResult) as raised:
                self.service.add(resource="bug", object_id=7, comment="hello", inline_image=image)

        self.assertTrue(raised.exception.details["possible_orphan"])
        self.api.post_comment.assert_not_called()
        self.assertEqual(1, self.api.upload_inline_image.call_count)

    def test_inline_comment_unknown_does_not_delete_reupload_or_repost(self) -> None:
        self.api.snapshot.side_effect = [snapshot([]), snapshot([])]
        self.api.get_comment_form.return_value = "uid-1"
        self.api.upload_inline_image.return_value = LegacyPageResponse(
            status=200,
            url="http://localhost/index.php?m=file&f=download&fileID=21",
            content_type="application/json",
            body=json.dumps({"fileID": 21, "url": "/file/21.png"}).encode(),
        )
        self.api.post_comment.side_effect = LegacyPageFailure(
            "connection lost", stage="comment", transport_uncertain=True
        )
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "image.png"
            image.write_bytes(b"png")
            with self.assertRaises(UnknownWriteResult) as raised:
                self.service.add(resource="bug", object_id=7, comment="hello", inline_image=image)

        self.assertTrue(raised.exception.details["possible_orphan"])
        self.assertEqual(1, self.api.upload_inline_image.call_count)
        self.assertEqual(1, self.api.post_comment.call_count)
        self.api.delete.assert_not_called()

    def test_legacy_inline_upload_response_extracts_file_id_from_url(self) -> None:
        response = LegacyPageResponse(
            status=200,
            url="http://localhost/index.php?m=file&f=ajaxUpload&uid=u",
            content_type="text/html",
            body=b'{"error":0,"url":"\\/index.php?m=file&f=read&t=png&fileID=42"}',
        )

        result = parse_inline_upload_response(response)

        self.assertEqual(42, result.file_id)
        self.assertEqual("/index.php?m=file&f=read&t=png&fileID=42", result.url)

    def test_api_snapshot_reads_nested_object_fields_when_actions_are_top_level(self) -> None:
        result = snapshot_from_detail(
            {
                "status": "success",
                "bug": {"status": "active", "title": "nested title", "product": 2},
                "actions": [],
            },
            object_type="bug",
        )

        self.assertEqual([], list(result.actions))
        self.assertEqual(
            {"status": "active", "title": "nested title", "product": 2},
            result.critical_fields,
        )

    def test_api_rejects_cross_origin_inline_upload_url(self) -> None:
        session = Mock()
        session.config = Mock(base_url="http://localhost", account="admin", password="secret")
        web = Mock()
        web.base_url = "http://localhost"
        web.upload_inline_image.return_value = LegacyPageResponse(
            status=200,
            url="http://localhost/index.php?m=file&f=ajaxUpload&uid=u",
            content_type="application/json",
            body=json.dumps({"fileID": 21, "url": "http://localhost:9999/image.png"}).encode(),
        )
        api = CommentAPI(session, web_client_factory=lambda **_: web)

        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "image.png"
            image.write_bytes(b"png")
            with self.assertRaises(ValueError):
                api.upload_inline_image(
                    object_type="bug",
                    object_id=7,
                    uid="u",
                    file=image,
                )

    def test_inline_comment_match_ignores_server_image_attributes(self) -> None:
        self.api.snapshot.side_effect = [
            snapshot([]),
            snapshot([action(
                11,
                body='hello<p><img onload="setImageSize(this,870)" src="/image.png" alt="image.png" /></p>',
            )]),
        ]
        self.api.get_comment_form.return_value = "uid-1"
        self.api.upload_inline_image.return_value = LegacyPageResponse(
            status=200,
            url="http://localhost/index.php?m=file&f=ajaxUpload&uid=u",
            content_type="application/json",
            body=json.dumps({"fileID": 21, "url": "/image.png"}).encode(),
        )

        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "image.png"
            image.write_bytes(b"png")
            result = self.service.add(resource="bug", object_id=7, comment="hello", inline_image=image)

        self.assertEqual(11, result["action_id"])

    def test_invalid_file_and_inline_paths_are_rejected_before_form_read(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file_path = Path(td) / "missing-attachment.txt"
            image_path = Path(td) / "missing-image.png"
            with self.assertRaises(UsageError):
                self.service.add(
                    resource="bug",
                    object_id=7,
                    comment="hello",
                    files=(file_path,),
                    inline_image=image_path,
                )
        self.api.snapshot.assert_not_called()
        self.api.get_comment_form.assert_not_called()

    def test_page_snapshot_reads_zentao_history_panel_and_normalizes_comment_files(self) -> None:
        panel = {
            "objectID": 7,
            "objectType": "bug",
            "actions": [{
                "id": 11,
                "action": "commented",
                "content": "2026-08-28, 由 <strong>admin</strong> 添加备注。",
                "comment": "<p>hello</p>",
                "historyChanges": '添加了 <strong><i>附件 </i></strong>"报告.txt"。',
                "files": [{"id": 21, "pathname": "202608/report", "extension": "txt", "size": 4}],
            }],
        }
        # ZenTao appends a JavaScript function after the JSON array in this
        # attribute, so the parser must decode the actions array prefix only.
        raw = json.dumps(panel, ensure_ascii=False)[:-1] + ',"fileActions":function(file){return file;}}'
        body = f'<div zui-create-historyPanel="{escape(raw, quote=True)}"></div>'.encode("utf-8")

        result = parse_page_snapshot(body, object_type="bug")

        self.assertEqual(1, len(result.actions))
        self.assertEqual("admin", result.actions[0]["actor"])
        self.assertEqual("bug", result.actions[0]["objectType"])
        self.assertEqual(7, result.actions[0]["objectID"])
        self.assertEqual("报告.txt", result.actions[0]["files"][0]["name"])
        self.assertEqual("comment", result.actions[0]["files"][0]["objectType"])
        self.assertEqual(11, result.actions[0]["files"][0]["objectID"])
        self.assertEqual("/index.php?m=file&f=download&fileID=21", result.actions[0]["files"][0]["url"])


if __name__ == "__main__":
    unittest.main()
