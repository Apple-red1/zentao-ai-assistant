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


def title_config(tmp_path):
    return AppConfig.model_validate({
        "personal": {"scopeNames": ["area-web", "area-api", "other-web", "other-api"]},
        "team": {"scopeNames": ["area-web"]},
        "repositories": {
            key: {
                "repository": key,
                "path": str(tmp_path / key),
                "targetBranch": "feature/fix",
                "testCommands": ["pytest"],
            }
            for key in ("area-web", "area-api", "other-web", "other-api")
        },
        "titleRouting": [
            {
                "marker": "【Synthetic Area】",
                "frontendRepository": "area-web",
                "backendRepository": "area-api",
                "frontendKeywords": ["widget"],
                "backendKeywords": ["worker"],
            },
            {
                "marker": "【Other Area】",
                "frontendRepository": "other-web",
                "backendRepository": "other-api",
            },
        ],
    })


def test_local_title_marker_routes_frontend_and_backend(tmp_path):
    cfg = title_config(tmp_path)
    frontend = route_bug(
        BugSnapshot(identifier="front", title="【Synthetic Area】 button cannot click"),
        cfg,
    )
    backend = route_bug(
        BugSnapshot(identifier="back", title="【Synthetic Area】 worker failed"),
        cfg,
    )
    assert frontend.selectedRepository == "area-web"
    assert frontend.layer == "frontend"
    assert {"button", "click"} <= set(frontend.matchedKeywords)
    assert backend.selectedRepository == "area-api"
    assert backend.layer == "backend"
    assert "worker" in backend.matchedKeywords


def test_explicit_title_layer_wins_over_url_tokens_in_description(tmp_path):
    result = route_bug(
        BugSnapshot(
            identifier="front-with-url",
            title="【Synthetic Area】 footer link cannot click",
            description="reproduce at https://example.invalid/api/preview",
        ),
        title_config(tmp_path),
    )
    assert result.selectedRepository == "area-web"
    assert result.layer == "frontend"


def test_local_title_marker_fails_closed_for_ambiguous_layer_or_marker(tmp_path):
    cfg = title_config(tmp_path)
    ambiguous_layer = route_bug(
        BugSnapshot(identifier="layer", title="【Synthetic Area】 button API"), cfg
    )
    conflicting_marker = route_bug(
        BugSnapshot(identifier="marker", title="【Synthetic Area】【Other Area】 button"), cfg
    )
    unmatched = route_bug(BugSnapshot(identifier="none", title="button"), cfg)
    assert ambiguous_layer.selectedRepository is None
    assert set(ambiguous_layer.candidates) == {"area-web", "area-api"}
    assert conflicting_marker.selectedRepository is None
    assert unmatched.selectedRepository is None
