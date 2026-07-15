import re
import unicodedata
from zentao_ai.config.models import AppConfig
from .models import BugSnapshot, RoutingDecision

FRONTEND = ("ui", "style", "page", "link", "页面", "样式", "链接", "前端")
BACKEND = ("api", "service", "database", "permission", "接口", "服务", "数据库", "权限", "后端")


def normalize_scope_name(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip()
    return "".join(chr(ord(char) + 32) if "A" <= char <= "Z" else char for char in normalized)


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
    for scope, mapping in config.repositories.items():
        markers = {scope.casefold(), mapping.repository.casefold()}
        def present(marker: str) -> bool:
            if marker.isascii():
                return re.search(rf"(?<![\w@.]){re.escape(marker)}(?![\w@.])", text) is not None
            return marker in text
        if any(marker and present(marker) for marker in markers):
            candidates.append(mapping.repository)
    candidates = list(dict.fromkeys(candidates))
    selected = candidates[0] if len(candidates) == 1 and (bool(exact_keys) or layer is not None) else None
    exact_selected = selected is not None and bool(exact_keys)
    return RoutingDecision(candidates=candidates, layer=layer, selectedRepository=selected, matchedKeywords=matches, confidence=1.0 if exact_selected else 0.8 if selected else 0.0, reasons=["EXACT_CONFIGURED_SCOPE"] if exact_selected else ["UNIQUE_MARKER_AND_LAYER"] if selected else ["ROUTING_NOT_UNIQUE"])
