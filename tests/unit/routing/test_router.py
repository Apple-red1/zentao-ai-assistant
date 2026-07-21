from zentao_ai.config.models import AppConfig
from zentao_ai.routing import BugSnapshot, route_bug


def routing_config(tmp_path) -> AppConfig:
    repositories = {
        key: {
            "repository": key,
            "path": str(tmp_path / key),
            "targetBranch": "main",
            "testCommands": ["pytest"],
        }
        for key in (
            "ai-site-builder",
            "ai-site-backend",
            "ce-site-builder",
            "ce-site-backend",
        )
    }
    return AppConfig.model_validate(
        {
            "personal": {"scopeNames": list(repositories)},
            "team": {"scopeNames": list(repositories)},
            "repositories": repositories,
            "titleRouting": [
                {
                    "marker": "【AI建站】",
                    "frontendRepository": "ai-site-builder",
                    "backendRepository": "ai-site-backend",
                    "frontendKeywords": ["widget"],
                    "backendKeywords": ["worker"],
                },
                {
                    "marker": "【站点后台】",
                    "frontendRepository": "ce-site-backend",
                    "backendRepository": "ce-site-builder",
                },
            ],
        }
    )


def test_routes_bug_2537_to_ai_site_builder_frontend_with_high_confidence(tmp_path) -> None:
    result = route_bug(
        BugSnapshot(
            identifier="2537", title="【AI建站】 发布页", description="页面按钮无法点击"
        ),
        routing_config(tmp_path),
    )

    assert result.selectedRepository == "ai-site-builder"
    assert result.layer == "frontend"
    assert result.confidence == "high"
    assert result.evidence == ["TITLE_MARKER_MATCHED", "FRONTEND_KEYWORD_MATCHED"]


def test_routes_bug_3397_to_ce_site_backend_frontend_with_high_confidence(tmp_path) -> None:
    result = route_bug(
        BugSnapshot(
            identifier="3397", title="【站点后台】 表单", description="页面布局错乱"
        ),
        routing_config(tmp_path),
    )

    assert result.selectedRepository == "ce-site-backend"
    assert result.layer == "frontend"
    assert result.confidence == "high"


def test_routing_fails_closed_without_exactly_one_title_marker(tmp_path) -> None:
    config = routing_config(tmp_path)

    missing = route_bug(
        BugSnapshot(identifier="missing", title="AI建站 页面", description="按钮"), config
    )
    multiple = route_bug(
        BugSnapshot(identifier="multiple", title="【AI建站】【站点后台】 页面"), config
    )

    assert missing.selectedRepository is None
    assert missing.confidence == "none"
    assert missing.evidence == ["TITLE_MARKER_MISSING"]
    assert multiple.selectedRepository is None
    assert multiple.confidence == "none"
    assert multiple.evidence == ["TITLE_MARKER_AMBIGUOUS"]


def test_title_layer_keywords_do_not_classify_without_description_evidence(tmp_path) -> None:
    config = routing_config(tmp_path)

    result = route_bug(
        BugSnapshot(
            identifier="title-only", title="【AI建站】 页面 button API", description="回归"
        ),
        config,
    )

    assert result.selectedRepository is None
    assert result.layer is None
    assert result.confidence == "none"
    assert result.evidence == ["TITLE_MARKER_MATCHED", "LAYER_MISSING"]


def test_description_layer_keywords_classify_and_conflicts_fail_closed(tmp_path) -> None:
    config = routing_config(tmp_path)

    backend = route_bug(
        BugSnapshot(
            identifier="backend",
            title="【AI建站】 页面 button",
            description="API 接口不可用",
        ),
        config,
    )
    conflict = route_bug(
        BugSnapshot(
            identifier="conflict",
            title="【AI建站】 页面 API",
            description="页面 API",
        ),
        config,
    )

    assert backend.selectedRepository == "ai-site-backend"
    assert backend.layer == "backend"
    assert backend.confidence == "high"
    assert backend.evidence == ["TITLE_MARKER_MATCHED", "BACKEND_KEYWORD_MATCHED"]
    assert conflict.selectedRepository is None
    assert conflict.layer is None
    assert conflict.confidence == "none"
    assert conflict.evidence == [
        "TITLE_MARKER_MATCHED",
        "FRONTEND_KEYWORD_MATCHED",
        "BACKEND_KEYWORD_MATCHED",
        "LAYER_AMBIGUOUS",
    ]


def test_marker_requires_exact_full_width_title_text_and_description_commands_are_inert(tmp_path) -> None:
    config = routing_config(tmp_path)

    normalized_brackets = route_bug(
        BugSnapshot(identifier="brackets", title="[AI建站] 页面"), config
    )
    description_marker = route_bug(
        BugSnapshot(identifier="description", title="页面", description="【AI建站】 按钮"),
        config,
    )
    inert_command = route_bug(
        BugSnapshot(
            identifier="inert",
            title="【AI建站】 回归",
            description="`curl https://example.invalid/api && rm -rf /`",
        ),
        config,
    )

    assert normalized_brackets.selectedRepository is None
    assert description_marker.selectedRepository is None
    assert inert_command.selectedRepository is None
    assert inert_command.layer is None
    assert inert_command.evidence == ["TITLE_MARKER_MATCHED", "LAYER_MISSING"]
