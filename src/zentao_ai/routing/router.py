from zentao_ai.config.models import AppConfig
from .models import BugSnapshot, RoutingDecision

FRONTEND = ("ui", "style", "page", "link", "页面", "样式", "链接", "前端")
BACKEND = ("api", "service", "database", "permission", "接口", "服务", "数据库", "权限", "后端")


def route_bug(snapshot: BugSnapshot, config: AppConfig) -> RoutingDecision:
    if snapshot.scope in config.repositories:
        item = config.repositories[snapshot.scope]
        return RoutingDecision(candidates=[item.repository], selectedRepository=item.repository, confidence=1.0, reasons=["EXACT_CONFIGURED_SCOPE"])
    text = f"{snapshot.title} {snapshot.description}".casefold()
    front = [word for word in FRONTEND if word.casefold() in text]
    back = [word for word in BACKEND if word.casefold() in text]
    layer = "frontend" if front and not back else "backend" if back and not front else None
    matches = front + back
    candidates = []
    for scope, mapping in config.repositories.items():
        markers = {scope.casefold(), mapping.repository.casefold(), *scope.casefold().replace("-", " ").split()}
        if any(marker and marker in text for marker in markers):
            candidates.append(mapping.repository)
    candidates = list(dict.fromkeys(candidates))
    selected = candidates[0] if len(candidates) == 1 and matches else None
    return RoutingDecision(candidates=candidates, layer=layer, selectedRepository=selected, matchedKeywords=matches, confidence=0.8 if selected else 0.0, reasons=["UNIQUE_MARKER_AND_LAYER"] if selected else ["ROUTING_NOT_UNIQUE"])
