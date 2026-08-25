
from __future__ import annotations

import importlib
import inspect
import unittest
from pathlib import Path

from ..support import CATALOG, SKILL_ROOT


class CatalogContractTest(unittest.TestCase):
    def test_official_snapshot_contains_all_120_endpoints(self) -> None:
        self.assertEqual(120, len(CATALOG))
        ids=[item["endpoint_id"] for item in CATALOG]
        self.assertEqual(120, len(set(ids)))
        required={"endpoint_id","resource","operation","method","path","official_doc","risk_class","internal_adapter","cli_command","skill_route","fake_route","fake_contract_test","cli_e2e_test","compatibility","parameters"}
        for item in CATALOG:
            self.assertTrue(required <= item.keys(), item["endpoint_id"])
            self.assertIn(item["risk_class"], {"R0","R1","R2","R3"})

    def test_all_internal_adapter_methods_are_explicit(self) -> None:
        actual=set()
        for item in CATALOG:
            if item["endpoint_id"] == "token.login":
                module=importlib.import_module("zentao_skill.internal.zentao.auth")
                cls=module.AuthAPI
            else:
                module_name, class_name, method_name = item["internal_adapter"].split(".")
                module=importlib.import_module(f"zentao_skill.internal.zentao.{module_name}")
                cls=getattr(module,class_name)
                method=getattr(cls,method_name)
                self.assertEqual(item["endpoint_id"], getattr(method,"__zentao_endpoint_id__",None))
            for _,method in inspect.getmembers(cls, inspect.isfunction):
                eid=getattr(method,"__zentao_endpoint_id__",None)
                if eid: actual.add(eid)
        self.assertEqual({x["endpoint_id"] for x in CATALOG}, actual)

    def test_risk_classes_follow_the_frozen_policy(self) -> None:
        self.assertEqual({"R0","R1","R2","R3"},{item["risk_class"] for item in CATALOG})
        for item in CATALOG:
            if item["method"] == "DELETE": expected="R3"
            elif item["action"] in {"resolve","close","activate","start","finish"}: expected="R2"
            elif item["method"] == "GET" or item["endpoint_id"] == "token.login": expected="R0"
            else: expected="R1"
            self.assertEqual(expected,item["risk_class"],item["endpoint_id"])

    def test_parameter_mapping_follows_human_cli_contract(self) -> None:
        for item in CATALOG:
            for location in ("path", "query", "body", "form"):
                for param in item["parameters"][location]:
                    self.assertNotIn("-i-d", param["cli"], (item["endpoint_id"], param))
        bug_create=next(item for item in CATALOG if item["endpoint_id"]=="bug.create")
        product=next(param for param in bug_create["parameters"]["body"] if param["api_name"]=="productID")
        self.assertEqual("--product", product["cli"])
        affected=next(param for param in bug_create["parameters"]["body"] if param["api_name"]=="openedBuild")
        self.assertEqual("--affected-build", affected["cli"]); self.assertTrue(affected["repeatable"])
        steps=next(param for param in bug_create["parameters"]["body"] if param["api_name"]=="steps")
        self.assertEqual("--steps-file", steps["file_variant"])

    def test_semantic_parameter_domains_are_explicit(self) -> None:
        by_id = {item["endpoint_id"]: item for item in CATALOG}

        def body_param(endpoint_id: str, api_name: str) -> dict[str, object]:
            return next(param for param in by_id[endpoint_id]["parameters"]["body"] if param["api_name"] == api_name)

        for endpoint_id, api_name in (
            ("bug.create", "story"), ("bug.edit", "story"),
            ("product.create", "line"), ("product.edit", "line"),
            ("story.create", "module"), ("story.create", "parent"),
            ("story.create", "execution"), ("story.edit", "module"),
            ("story.edit", "parent"), ("test-case.create", "module"),
            ("test-case.edit", "module"), ("user.edit", "dept"),
        ):
            param = body_param(endpoint_id, api_name)
            self.assertEqual("non_negative_relation_id", param.get("domain"), (endpoint_id, api_name))
            self.assertEqual(0, param.get("minimum"), (endpoint_id, api_name))

        resolved_build = body_param("bug.resolve", "resolvedBuild")
        self.assertEqual("build_reference", resolved_build.get("domain"))
        self.assertEqual(["trunk"], resolved_build.get("allowed_special_values"))

    def test_protocol_field_names_stay_out_of_cli_and_services(self) -> None:
        forbidden=("assignedTo", "openedBuild", "pageID", "recPerPage", "resolvedDate", "resolvedBuild", "productID", "projectID", "executionID", "programID")
        for area in (SKILL_ROOT/"scripts"/"zentao_skill"/"cli", SKILL_ROOT/"scripts"/"zentao_skill"/"services"):
            for path in area.rglob("*.py"):
                text=path.read_text(encoding="utf-8")
                for token in forbidden:
                    self.assertNotIn(token, text, (path, token))

    def test_skill_routes_exist_and_name_every_endpoint(self) -> None:
        for item in CATALOG:
            path=SKILL_ROOT/item["skill_route"]
            self.assertTrue(path.is_file(), item["endpoint_id"])
            self.assertIn(item["endpoint_id"], path.read_text(encoding="utf-8"))

    def test_fake_and_test_indexes_resolve_to_real_files_and_anchors(self) -> None:
        for item in CATALOG:
            fake_file, fake_anchor=item["fake_route"].split("#",1)
            fake_path=SKILL_ROOT/fake_file
            self.assertTrue(fake_path.is_file(),item["endpoint_id"])
            self.assertIn(fake_anchor,fake_path.read_text(encoding="utf-8"),item["endpoint_id"])
            for field in ("fake_contract_test","cli_e2e_test"):
                file_name, anchor=item[field].split("#",1)
                path=SKILL_ROOT/file_name
                self.assertTrue(path.is_file(),(item["endpoint_id"],field))
                self.assertIn(f"def {anchor}(",path.read_text(encoding="utf-8"),(item["endpoint_id"],field))


if __name__ == "__main__": unittest.main()
