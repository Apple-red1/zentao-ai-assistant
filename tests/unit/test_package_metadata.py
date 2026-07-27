from importlib.metadata import metadata

import zentao_ai


def test_package_identity() -> None:
    package = metadata("zentao-ai-assistant")
    assert package["Version"] == "0.1.0"
    assert zentao_ai.__version__ == "0.1.0"
