from __future__ import annotations

import base64
import datetime as dt
from typing import Any

from cremalink.parsing.monitor.extractors import extract_fields_from_b64
from cremalink.parsing.monitor.model import MonitorSnapshot


def decode_monitor_b64(raw_b64: str) -> bytes:
    try:
        return base64.b64decode(raw_b64)
    except Exception as exc:
        raise ValueError(f"Failed to decode monitor base64: {exc}") from exc


def build_monitor_snapshot(
    payload: dict[str, Any],
    source: str = "local",
    device_id: str | None = None,
) -> MonitorSnapshot:
    raw_b64 = payload.get("monitor_b64") or payload.get("monitor", {}).get("data", {}).get("value")
    if not raw_b64:
        return MonitorSnapshot(
            raw=b"",
            raw_b64="",
            received_at=dt.datetime.fromtimestamp(payload.get("received_at") or dt.datetime.now(dt.UTC).timestamp()),
            parsed={},
            warnings=["no monitor_b64 in payload"],
            errors=[],
            source=source,
            device_id=device_id,
        )

    raw = decode_monitor_b64(raw_b64)
    parsed, warnings, errors, frame = extract_fields_from_b64(raw_b64)
    return MonitorSnapshot(
        raw=raw,
        raw_b64=raw_b64,
        received_at=dt.datetime.fromtimestamp(payload.get("received_at") or dt.datetime.now(dt.UTC).timestamp()),
        parsed=parsed,
        warnings=warnings,
        errors=errors,
        source=source,
        device_id=device_id,
        frame=frame,
    )
