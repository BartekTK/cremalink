from __future__ import annotations

import base64
from typing import Any, Tuple

from cremalink.parsing.monitor.frame import MonitorFrame


def extract_fields_from_b64(raw_b64: str) -> Tuple[dict[str, Any], list[str], list[str], MonitorFrame | None]:
    parsed: dict[str, Any] = {}
    warnings: list[str] = []
    errors: list[str] = []
    frame: MonitorFrame | None = None
    try:
        frame = MonitorFrame.from_b64(raw_b64)
    except Exception as exc:
        errors.append(f"parse_failed: {exc}")
        try:
            raw = base64.b64decode(raw_b64)
            parsed["raw_length"] = len(raw)
        except Exception:
            pass
        return parsed, warnings, errors, frame

    parsed.update(
        {
            "accessory": frame.accessory,
            "switches": list(frame.switches),
            "alarms": list(frame.alarms),
            "status": frame.status,
            "action": frame.action,
            "progress": frame.progress,
            "direction": frame.direction,
            "request_id": frame.request_id,
            "answer_required": frame.answer_required,
            "timestamp": frame.timestamp.hex() if frame.timestamp else "",
            "extra": frame.extra.hex() if frame.extra else "",
        }
    )

    return parsed, warnings, errors, frame
