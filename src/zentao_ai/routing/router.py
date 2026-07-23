from __future__ import annotations

import re
import unicodedata

from zentao_ai.config.models import AppConfig, TitleRoutingConfig

from .models import BugSnapshot, RoutingDecision

FRONTEND_KEYWORDS = (
    "ui",
    "style",
    "page",
    "link",
    "button",
    "layout",
    "interaction",
    "click",
    "frontend",
    "页面",
    "样式",
    "链接",
    "按钮",
    "布局",
    "交互",
    "点击",
    "前端",
)
BACKEND_KEYWORDS = (
    "api",
    "service",
    "database",
    "permission",
    "backend",
    "接口",
    "服务",
    "数据库",
    "权限",
    "后端",
)
_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`]*`")
_URL = re.compile(r"https?://[^\s`]+", re.IGNORECASE)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def normalize_scope_name(value: str) -> str:
    """Normalize repository scope names for existing repository safety checks."""
    return unicodedata.normalize("NFC", value).strip().casefold()


def _classification_text(description: str) -> str:
    """Return normalized description prose only; Bug commands and URLs are inert."""
    description_without_code = _FENCED_CODE.sub(" ", description)
    description_without_code = _INLINE_CODE.sub(" ", description_without_code)
    description_without_urls = _URL.sub(" ", description_without_code)
    return _normalize(description_without_urls)


def _matches_keyword(text: str, keyword: str) -> bool:
    normalized = _normalize(keyword)
    if not normalized:
        return False
    if normalized.isascii() and normalized.replace("_", "").isalnum():
        return re.search(rf"(?<![\w]){re.escape(normalized)}(?![\w])", text) is not None
    return normalized in text


def _layer_keywords(mapping: TitleRoutingConfig) -> tuple[tuple[str, ...], tuple[str, ...]]:
    frontend = tuple(dict.fromkeys((*FRONTEND_KEYWORDS, *mapping.frontendKeywords)))
    backend = tuple(dict.fromkeys((*BACKEND_KEYWORDS, *mapping.backendKeywords)))
    return frontend, backend


def _decision_without_marker(evidence: str) -> RoutingDecision:
    return RoutingDecision(evidence=[evidence])


def route_bug(snapshot: BugSnapshot, config: AppConfig) -> RoutingDecision:
    """Route untrusted Bug text using one configured title marker and one layer."""
    title = _normalize(snapshot.title)
    matches = [mapping for mapping in config.titleRouting if _normalize(mapping.marker) in title]
    if not matches:
        return _decision_without_marker("TITLE_MARKER_MISSING")
    if len(matches) != 1:
        return _decision_without_marker("TITLE_MARKER_AMBIGUOUS")

    mapping = matches[0]
    text = _classification_text(snapshot.description)
    frontend_keywords, backend_keywords = _layer_keywords(mapping)
    frontend = [keyword for keyword in frontend_keywords if _matches_keyword(text, keyword)]
    backend = [keyword for keyword in backend_keywords if _matches_keyword(text, keyword)]
    evidence = ["TITLE_MARKER_MATCHED"]
    if frontend:
        evidence.append("FRONTEND_KEYWORD_MATCHED")
    if backend:
        evidence.append("BACKEND_KEYWORD_MATCHED")

    candidates = [
        config.repositories[mapping.frontendRepository].repository,
        config.repositories[mapping.backendRepository].repository,
    ]
    if frontend and backend:
        return RoutingDecision(
            candidates=candidates,
            matchedKeywords=frontend + backend,
            evidence=[*evidence, "LAYER_AMBIGUOUS"],
        )
    if not frontend and not backend:
        return RoutingDecision(candidates=candidates, evidence=[*evidence, "LAYER_MISSING"])

    layer = "frontend" if frontend else "backend"
    selected = (
        config.repositories[mapping.frontendRepository].repository
        if layer == "frontend"
        else config.repositories[mapping.backendRepository].repository
    )
    return RoutingDecision(
        candidates=[selected],
        layer=layer,
        selectedRepository=selected,
        matchedKeywords=frontend if layer == "frontend" else backend,
        confidence="high",
        evidence=evidence,
    )
