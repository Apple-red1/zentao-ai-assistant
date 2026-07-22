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


def title_config(tmp_path):
    return AppConfig.model_validate({
        "personal": {"scopeNames": ["ce-site-backend", "cms-center"]},
        "team": {"scopeNames": ["ce-site-backend", "cms-center"]},
        "repositories": {
            "ce-site-backend": {"repository": "ce-site-backend", "path": str(tmp_path / "web"), "targetBranch": "wwt_play", "testCommands": ["pytest"]},
            "cms-center": {"repository": "cms-center", "path": str(tmp_path / "api"), "targetBranch": "main", "testCommands": ["pytest"]},
        },
        "titleRouting": [
            {"marker": "【站点后台】", "frontendRepository": "ce-site-backend", "backendRepository": "cms-center"}
        ],
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


def test_exact_scope_is_unicode_casefolded_and_has_priority_without_layer(tmp_path):
    assert route_bug(BugSnapshot(identifier="x", title="UI", scope="SITE"), config(tmp_path)).selectedRepository == "example-web"
    exact = route_bug(BugSnapshot(identifier="x", title="unknown", scope="SITE"), config(tmp_path))
    assert exact.selectedRepository == "example-web" and exact.confidence == 1.0


def test_exact_scope_suppresses_conflicting_marker_inference(tmp_path):
    result = route_bug(BugSnapshot(identifier="x", scope="site", title="AI UI"), config(tmp_path))
    assert result.selectedRepository == "example-web"
    assert result.candidates == ["example-web"]


def test_exact_scope_lowercases_non_ascii_letters(tmp_path):
    cfg = config(tmp_path)
    repository = cfg.repositories.pop("site")
    cfg.repositories["ÉΛΛΑ"] = repository
    result = route_bug(BugSnapshot(identifier="x", scope="éλλα", title="unknown"), cfg)
    assert result.selectedRepository == "example-web"


def test_marker_uses_token_boundaries_and_does_not_match_email(tmp_path):
    result = route_bug(BugSnapshot(identifier="x", title="UI user@site.example"), config(tmp_path))
    assert result.selectedRepository is None


def test_site_admin_login_button_routes_to_frontend_repository(tmp_path):
    result = route_bug(
        BugSnapshot(
            identifier="3397",
            title="【站点后台】登录按钮背景色改为白色，文字改为黑色",
            description="登录页按钮当前为黑底白字",
        ),
        title_config(tmp_path),
    )
    assert result.selectedRepository == "ce-site-backend"
    assert result.layer == "frontend"
    assert result.confidence == 0.9
