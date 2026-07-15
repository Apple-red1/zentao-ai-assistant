from zentao_ai.config.models import AppConfig
from zentao_ai.routing import BugSnapshot, route_bug


def config(tmp_path):
    return AppConfig.model_validate({
        "personal": {"scopeNames": ["site", "ai"]},
        "team": {"scopeNames": ["site", "ai"]},
        "repositories": {
            "site": {"repository": "example-web", "path": str(tmp_path / "web"), "targetBranch": "main", "testCommands": ["pytest"]},
            "ai": {"repository": "example-ai-web", "path": str(tmp_path / "ai"), "targetBranch": "main", "testCommands": ["pytest"]},
        },
    })


def test_exact_configured_scope_wins(tmp_path):
    result = route_bug(BugSnapshot(identifier="BUG-1001", title="API", scope="site"), config(tmp_path))
    assert result.selectedRepository == "example-web"
    assert result.confidence == 1.0


def test_markers_and_layer_select_unique_repository(tmp_path):
    result = route_bug(BugSnapshot(identifier="BUG-1002", title="AI 建站 UI 页面", description="style link"), config(tmp_path))
    assert result.selectedRepository == "example-ai-web"
    assert result.layer == "frontend"
    assert {"ui", "页面", "style", "link"} <= set(result.matchedKeywords)


def test_ambiguous_or_unmatched_routes_fail_closed(tmp_path):
    assert route_bug(BugSnapshot(identifier="x", title="UI"), config(tmp_path)).selectedRepository is None
    assert route_bug(BugSnapshot(identifier="x", title="unknown"), config(tmp_path)).selectedRepository is None


def test_backend_keywords_are_case_insensitive(tmp_path):
    result = route_bug(BugSnapshot(identifier="x", title="AI API DataBase PERMISSION"), config(tmp_path))
    assert result.layer == "backend"
