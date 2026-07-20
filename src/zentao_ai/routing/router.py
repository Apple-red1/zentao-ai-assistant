import re
import unicodedata
from zentao_ai.config.models import AppConfig
from .models import BugSnapshot, RoutingDecision

FRONTEND = (
    "ui", "style", "page", "link", "button", "layout", "interaction", "click",
    "页面", "样式", "链接", "按钮", "布局", "交互", "点击", "前端",
)
BACKEND = ("api", "service", "database", "permission", "接口", "服务", "数据库", "权限", "后端")


def normalize_scope_name(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip().lower()


def route_bug(snapshot: BugSnapshot, config: AppConfig) -> RoutingDecision:
    text = unicodedata.normalize("NFC", f"{snapshot.title} {snapshot.description}").casefold()
    front = [word for word in FRONTEND if word.casefold() in text]
    back = [word for word in BACKEND if word.casefold() in text]
    layer = "frontend" if front and not back else "backend" if back and not front else None
    matches = front + back
    exact_keys = [key for key in config.repositories if snapshot.scope and normalize_scope_name(key) == normalize_scope_name(snapshot.scope)]
    candidates = [config.repositories[key].repository for key in exact_keys]
    if len(candidates) == 1:
        return RoutingDecision(candidates=candidates, layer=layer, selectedRepository=candidates[0], matchedKeywords=matches, confidence=1.0, reasons=["EXACT_CONFIGURED_SCOPE"])
    title_matches = [
        mapping
        for mapping in config.titleRouting
        if unicodedata.normalize("NFC", mapping.marker).casefold() in text
    ]
    if title_matches:
        local_front = list(front)
        local_back = list(back)
        for title_mapping in title_matches:
            local_front.extend(
                keyword
                for keyword in title_mapping.frontendKeywords
                if keyword.casefold() in text
            )
            local_back.extend(
                keyword
                for keyword in title_mapping.backendKeywords
                if keyword.casefold() in text
            )
        local_front = list(dict.fromkeys(local_front))
        local_back = list(dict.fromkeys(local_back))
        local_layer = (
            "frontend"
            if local_front and not local_back
            else "backend"
            if local_back and not local_front
            else None
        )
        title_candidates = list(
            dict.fromkeys(
                repository
                for title_mapping in title_matches
                for repository in (
                    config.repositories[title_mapping.frontendRepository].repository,
                    config.repositories[title_mapping.backendRepository].repository,
                )
            )
        )
        selected = None
        if len(title_matches) == 1 and local_layer is not None:
            repository_key = (
                title_matches[0].frontendRepository
                if local_layer == "frontend"
                else title_matches[0].backendRepository
            )
            selected = config.repositories[repository_key].repository
        return RoutingDecision(
            candidates=title_candidates,
            layer=local_layer,
            selectedRepository=selected,
            matchedKeywords=local_front + local_back,
            confidence=0.9 if selected else 0.0,
            reasons=["LOCAL_TITLE_MARKER_AND_LAYER"] if selected else ["LOCAL_TITLE_ROUTING_AMBIGUOUS"],
        )
    for scope, repository_mapping in config.repositories.items():
        markers = {scope.casefold(), repository_mapping.repository.casefold()}
        def present(marker: str) -> bool:
            if marker.isascii():
                return re.search(rf"(?<![\w@.]){re.escape(marker)}(?![\w@.])", text) is not None
            return marker in text
        if any(marker and present(marker) for marker in markers):
            candidates.append(repository_mapping.repository)
    candidates = list(dict.fromkeys(candidates))
    selected = candidates[0] if len(candidates) == 1 and (bool(exact_keys) or layer is not None) else None
    exact_selected = selected is not None and bool(exact_keys)
    return RoutingDecision(candidates=candidates, layer=layer, selectedRepository=selected, matchedKeywords=matches, confidence=1.0 if exact_selected else 0.8 if selected else 0.0, reasons=["EXACT_CONFIGURED_SCOPE"] if exact_selected else ["UNIQUE_MARKER_AND_LAYER"] if selected else ["ROUTING_NOT_UNIQUE"])
