
from __future__ import annotations

import importlib
import re
import unittest
from pathlib import Path
from typing import Any

from ..fake_zentao.server import FakeZenTao
from ..support import CATALOG, SAMPLES, materialize
from zentao_skill.internal.config import Config
from zentao_skill.internal.http.client import HttpClient
from zentao_skill.internal.zentao.auth import AuthAPI
from zentao_skill.internal.zentao.executions import normalize_plans
from zentao_skill.internal.zentao.session import ZentaoSession

CONTRACT_ENDPOINT_IDS = frozenset(item["endpoint_id"] for item in CATALOG)


def mapped(param: dict[str, Any], value: Any) -> Any:
    enum_map=param.get("enum_map", {})
    if isinstance(value,list): return [mapped(param,item) for item in value]
    if isinstance(value,dict): return value
    return enum_map.get(value,value)


def expected_query(item: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    result={}
    for param in item["parameters"]["query"]:
        if param["api_name"] == "orderBy":
            sort=kwargs.get("sort")
            if sort is not None:
                result["orderBy"]=f"{str(sort).replace('-', '_')}_{kwargs.get('order') or 'asc'}"
            continue
        value=kwargs.get(param["argument"])
        if value is None: continue
        value=mapped(param,value)
        result[param["api_name"]]=[str(v) for v in value] if isinstance(value,list) else str(value)
    return result


def expected_body(item: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    result={}
    for param in item["parameters"]["body"]:
        value=kwargs.get(param["argument"])
        if value is not None:
            if param["api_name"] == "plans": value=normalize_plans(value, kwargs.get("product"))
            result[param["api_name"]]=mapped(param,value)
    for param in item.get("compatibility_parameters", {}).get("body", []):
        value=kwargs.get(param["argument"])
        if value is not None:
            result[param["api_name"]]=mapped(param,value)
    for param in item["parameters"]["form"]:
        value=kwargs.get(param["argument"])
        if value is None: continue
        if param["api_name"] == "file": value=Path(str(value)).name
        elif isinstance(value,list): value=[str(v) for v in value]
        else: value=str(value)
        result[param["api_name"]]=mapped(param,value)
    return result


class ContractTests(unittest.TestCase):
    def test_all_120_internal_adapters_match_request_and_state_contract(self) -> None:
        with FakeZenTao() as fake:
            for item in CATALOG:
                with self.subTest(endpoint=item["endpoint_id"]):
                    fake.state.reset()
                    kwargs=materialize(SAMPLES[item["endpoint_id"]]["adapter_kwargs"])
                    if item["endpoint_id"] == "token.login":
                        result=AuthAPI(fake.base_url, HttpClient(timeout=1)).login(**kwargs)
                        self.assertEqual("fake-token",result)
                    else:
                        session=ZentaoSession(Config(fake.base_url,"admin","secret"),http=HttpClient(timeout=1),retry_delays=(0,0),token_cache=False)
                        module_name,class_name,method_name=item["internal_adapter"].split(".")
                        module=importlib.import_module(f"zentao_skill.internal.zentao.{module_name}")
                        result=getattr(getattr(module,class_name)(session),method_name)(**kwargs)
                        self.assertIsInstance(result,dict)
                    request=fake.state.requests[-1]
                    self.assertEqual(item["endpoint_id"],request["endpoint_id"])
                    self.assertEqual(item["method"],request["method"])
                    self.assertEqual(re.sub(r"\{[^}]+\}","1",item["path"]),request["path"])
                    self.assertEqual(expected_query(item,kwargs),request["query"])
                    self.assertEqual(expected_body(item,kwargs),request["body"])
                    if item["endpoint_id"] == "token.login": continue
                    bucket=fake.state.resources[item["resource"]]
                    if item["method"] == "DELETE":
                        self.assertNotIn("1",bucket)
                        self.assertEqual("success",result["status"])
                    elif item["method"] == "POST":
                        self.assertIn(str(result["id"]),bucket)
                    elif item["risk_class"] == "R2":
                        expected={"resolve":"resolved","close":"closed","activate":"active","start":"doing","finish":"done"}[item["action"]]
                        self.assertEqual(expected,bucket["1"]["status"])


if __name__ == "__main__": unittest.main()
