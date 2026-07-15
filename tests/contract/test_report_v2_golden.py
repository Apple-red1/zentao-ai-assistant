import hashlib
import json
from pathlib import Path

import pytest

from zentao_ai.reporting import render_personal, render_team


FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.parametrize(
    ("mode", "renderer", "expected_sha256"),
    [
        ("personal", render_personal, "e879fb57c5ef29ca74376f44adf8517b4561ac8971568fce72dbd253252f3494"),
        ("team", render_team, "ee390d976217c1eb46e89f36c4882215ce2db70c059e77684104fe600d32b108"),
    ],
)
def test_v2_renderer_matches_utf8_lf_golden(mode, renderer, expected_sha256):
    payload = json.loads((FIXTURES / f"{mode}-report.json").read_text(encoding="utf-8"))
    expected = (FIXTURES / "golden" / f"{mode}-v2.md").read_bytes()

    assert expected.startswith(b"#")
    assert b"\r" not in expected
    assert expected.endswith(b"\n") and not expected.endswith(b"\n\n")
    assert hashlib.sha256(expected).hexdigest() == expected_sha256
    assert renderer(payload).encode("utf-8") == expected
