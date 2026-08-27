
from __future__ import annotations

import json
import os
import atexit
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

CATALOG = json.loads((SKILL_ROOT / "references" / "api-v2" / "endpoints.json").read_text(encoding="utf-8"))["endpoints"]
SAMPLES = json.loads((SKILL_ROOT / "tests" / "fixtures" / "endpoint_samples.json").read_text(encoding="utf-8"))
FIXTURE_FILE = SKILL_ROOT / "tests" / "fixtures" / "files" / "sample.txt"
CLI = SKILL_ROOT / "scripts" / "zentao.py"
TEST_HOME = Path(tempfile.mkdtemp(prefix="zentao-skill-test-home-"))


@atexit.register
def _remove_test_home() -> None:
    shutil.rmtree(TEST_HOME, ignore_errors=True)


def fake_env(base_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("ZENTAO_TOKEN_CACHE_DIR", None)
    env["HOME"] = str(TEST_HOME)
    env["USERPROFILE"] = str(TEST_HOME)
    config_path = TEST_HOME / ".zentao-ai-assistant" / "config.env"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        f"ZENTAO_BASE_URL=\"{base_url}\"\n"
        "ZENTAO_ACCOUNT=\"admin\"\n"
        "ZENTAO_PASSWORD=\"secret\"\n",
        encoding="utf-8",
    )
    if os.name == "posix":
        config_path.chmod(0o600)
        config_path.parent.chmod(0o700)
    env.update({
        "ZENTAO_CONFIG_FILE": str(config_path),
        "ZENTAO_BASE_URL": base_url,
        "ZENTAO_ACCOUNT": "admin",
        "ZENTAO_PASSWORD": "secret",
        "ZENTAO_TOKEN_CACHE_DISABLED": "1",
    })
    return env


def materialize(value: object) -> object:
    if value == "${FIXTURE_FILE}": return str(FIXTURE_FILE)
    if isinstance(value, list): return [materialize(v) for v in value]
    if isinstance(value, dict): return {k: materialize(v) for k,v in value.items()}
    return value


def run_cli(base_url: str, argv: list[str]) -> subprocess.CompletedProcess[str]:
    args=[str(FIXTURE_FILE) if x=="${FIXTURE_FILE}" else x for x in argv]
    return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, env=fake_env(base_url), timeout=10)


def run_cli_batch(base_url: str, cases: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
    payload=[]
    for case in cases:
        argv=[str(FIXTURE_FILE) if x=="${FIXTURE_FILE}" else x for x in case["argv"]]
        payload.append({"endpoint_id": case["endpoint_id"], "argv": argv})
    driver=SKILL_ROOT / "tests" / "e2e" / "cli_batch_driver.py"
    return subprocess.run(
        [sys.executable, str(driver)],
        input=json.dumps(payload), text=True, capture_output=True, env=fake_env(base_url), timeout=60,
    )


def internal_endpoint_ids() -> frozenset[str]:
    import importlib

    actual: set[str] = set()
    for item in CATALOG:
        module_name, class_name, method_name = item["internal_adapter"].split(".")
        module = importlib.import_module(f"zentao_skill.internal.zentao.{module_name}")
        method = getattr(getattr(module, class_name), method_name, None)
        if method is not None and getattr(method, "__zentao_endpoint_id__", None) == item["endpoint_id"]:
            actual.add(item["endpoint_id"])
    return frozenset(actual)


def skill_route_endpoint_ids() -> frozenset[str]:
    actual: set[str] = set()
    for item in CATALOG:
        path = SKILL_ROOT / item["skill_route"]
        if path.is_file() and item["endpoint_id"] in path.read_text(encoding="utf-8"):
            actual.add(item["endpoint_id"])
    return frozenset(actual)
