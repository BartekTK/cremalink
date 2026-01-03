from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class PropertiesSnapshot:
    raw: dict[str, Any]
    received_at: Optional[datetime]
    parsed: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        if name in self.raw:
            return self.raw[name]

        for entry in self.raw.values():
            if isinstance(entry, dict) and entry.get("property", {}).get("name") == name:
                return entry
        return None
