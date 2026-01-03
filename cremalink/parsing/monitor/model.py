from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from cremalink.parsing.monitor.frame import MonitorFrame


@dataclass
class MonitorSnapshot:
    raw: bytes
    raw_b64: str
    received_at: datetime
    parsed: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    source: str = "local"
    device_id: Optional[str] = None
    frame: Optional[MonitorFrame] = None
