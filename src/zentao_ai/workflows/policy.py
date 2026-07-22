from __future__ import annotations

import unicodedata
from collections.abc import Sequence

from zentao_ai.zentao.models import BugSnapshot

from .models import AnalysisPhase, AnalysisSignal


LOGIN_STYLE_TERMS = (
    "登录页",
    "登录按钮",
    "按钮",
    "背景色",
    "文字",
    "颜色",
    "白色",
    "黑色",
    "样式",
    "style",
    "button",
    "color",
)

PROTECTED_LOGIN_TERMS = (
    "接口",
    "api",
    "token",
    "密码",
    "password",
    "认证",
    "鉴权",
    "权限",
    "授权",
    "登录逻辑",
    "登录流程",
    "cookie",
    "session",
)


def _text(snapshot: BugSnapshot) -> str:
    return unicodedata.normalize("NFC", f"{snapshot.title}\n{snapshot.steps}").casefold()


def is_login_page_style_only(snapshot: BugSnapshot) -> bool:
    text = _text(snapshot)
    has_login = "登录页" in text or "登录按钮" in text
    has_style = any(term.casefold() in text for term in LOGIN_STYLE_TERMS)
    protected = any(term.casefold() in text for term in PROTECTED_LOGIN_TERMS)
    routing = snapshot.routing
    frontend_route = routing is not None and routing.layer == "frontend"
    return has_login and has_style and not protected and frontend_route


def default_analysis_signal(
    snapshot: BugSnapshot,
    history: Sequence[object],
    phase: AnalysisPhase,
) -> AnalysisSignal:
    del history
    if is_login_page_style_only(snapshot):
        return AnalysisSignal()
    text = _text(snapshot)
    if "登录" in text and any(term.casefold() in text for term in PROTECTED_LOGIN_TERMS):
        return AnalysisSignal(needsEngineerReview=True)
    if phase is AnalysisPhase.PRECHECK:
        return AnalysisSignal()
    return AnalysisSignal(needsEngineerReview=True)
