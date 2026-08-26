from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "skills" / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from zentao.identity import (  # noqa: E402
    AmbiguousMatchError,
    MatchNotFoundError,
    resolve_named_entity,
    resolve_user,
)


class SharedIdentityTests(unittest.TestCase):
    def test_exact_account_wins_over_exact_name(self) -> None:
        users = [
            {"id": 1, "account": "alice", "realname": "另一位 Alice"},
            {"id": 2, "account": "bob", "realname": "alice"},
        ]

        self.assertIs(resolve_user(users, "alice"), users[0])

    def test_unique_realname_and_name_are_exact_matches(self) -> None:
        users = [{"id": 1, "account": "zhangsan", "realname": "张三"}]
        entities = [{"id": 2, "name": "产品 A"}]

        self.assertIs(resolve_user(users, "张三"), users[0])
        self.assertIs(resolve_user(users, "zhangsan"), users[0])
        self.assertIs(resolve_named_entity(entities, "产品 A", kind="product"), entities[0])

    def test_user_name_alias_is_an_exact_match(self) -> None:
        users = [{"id": 1, "account": "user-a", "name": "显示名"}]
        self.assertIs(resolve_user(users, "显示名"), users[0])

    def test_duplicate_user_reports_safe_candidates_in_input_order(self) -> None:
        users = [
            {"id": 1, "account": "alice", "realname": "张三", "password": "secret-1"},
            {"id": 2, "account": "alice2", "realname": "张三", "email": "private@example.test"},
        ]

        with self.assertRaises(AmbiguousMatchError) as raised:
            resolve_user(users, "张三")

        error = raised.exception
        self.assertEqual("user", error.kind)
        self.assertEqual("张三", error.value)
        self.assertEqual(["alice", "alice2"], error.candidates)
        self.assertNotIn("password", repr(error))
        self.assertNotIn("email", repr(error))

    def test_duplicate_entity_reports_safe_candidates_in_input_order(self) -> None:
        entities = [
            {"id": 10, "name": "同名对象", "description": "private-1"},
            {"id": 11, "title": "同名对象", "token": "private-2"},
        ]

        with self.assertRaises(AmbiguousMatchError) as raised:
            resolve_named_entity(entities, "同名对象", kind="project")

        self.assertEqual("project", raised.exception.kind)
        self.assertEqual(["10", "11"], raised.exception.candidates)

    def test_positive_numeric_id_12_is_resolved_by_id_only(self) -> None:
        entities = [
            {"id": 12, "name": "通过 ID 命中"},
            {"id": 13, "name": "12"},
        ]

        self.assertIs(resolve_named_entity(entities, "12", kind="execution"), entities[0])
        self.assertIs(resolve_named_entity(entities, 12, kind="execution"), entities[0])

    def test_non_positive_numeric_values_use_exact_name_or_title(self) -> None:
        entities = [
            {"id": 12, "name": "0"},
            {"id": 13, "title": "-1"},
        ]

        self.assertIs(resolve_named_entity(entities, "0", kind="project"), entities[0])
        self.assertIs(resolve_named_entity(entities, "-1", kind="project"), entities[1])

    def test_not_found_exposes_kind_and_value(self) -> None:
        with self.assertRaises(MatchNotFoundError) as raised:
            resolve_named_entity([{"id": 1, "name": "现有对象"}], "不存在", kind="project")

        self.assertEqual("project", raised.exception.kind)
        self.assertEqual("不存在", raised.exception.value)

    def test_account_case_fallback_is_exact_and_ambiguous_case_is_not_guessed(self) -> None:
        users = [{"id": 1, "account": "alice", "realname": "Alice"}]
        self.assertIs(resolve_user(users, "ALICE"), users[0])

        with self.assertRaises(AmbiguousMatchError) as raised:
            resolve_user(
                [
                    {"id": 1, "account": "alice"},
                    {"id": 2, "account": "ALICE"},
                ],
                "Alice",
            )
        self.assertEqual(["alice", "ALICE"], raised.exception.candidates)

    def test_name_matching_is_case_sensitive_and_not_fuzzy(self) -> None:
        users = [{"id": 1, "account": "user-a", "realname": "Alice"}]
        entities = [{"id": 2, "name": "Alpha release"}]

        with self.assertRaises(MatchNotFoundError):
            resolve_user(users, "alice")
        with self.assertRaises(MatchNotFoundError):
            resolve_named_entity(entities, "Alpha", kind="release")
        with self.assertRaises(MatchNotFoundError):
            resolve_named_entity(entities, " Alpha release ", kind="release")


if __name__ == "__main__":
    unittest.main()
