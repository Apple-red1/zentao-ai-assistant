from pydantic import BaseModel, Field


class BugSnapshot(BaseModel):
    identifier: str
    title: str = ""
    description: str = ""
    scope: str | None = None


class RoutingDecision(BaseModel):
    candidates: list[str] = Field(default_factory=list)
    layer: str | None = None
    selectedRepository: str | None = None
    matchedKeywords: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasons: list[str] = Field(default_factory=list)
