
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    endpoint_id: str
    method: str
    path: str
    resource: str
    operation: str
    required_query: tuple[str, ...] = ()
    required_body: tuple[str, ...] = ()
    enum_values: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @property
    def regex(self) -> re.Pattern[str]:
        pattern = re.escape(self.path)
        for name in re.findall(r"\{([A-Za-z0-9_]+)\}", self.path):
            pattern = pattern.replace(re.escape("{" + name + "}"), f"(?P<{name}>[1-9][0-9]*)")
        return re.compile("^" + pattern + "$")
