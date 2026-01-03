from __future__ import annotations

import json
import pathlib
import tempfile
from pathlib import Path
from typing import Any, List
from importlib import resources


class DeviceMapNotFoundError(FileNotFoundError):
    pass


def _normalize_model_id(model_id: str) -> str:
    if not model_id or not model_id.strip():
        raise ValueError("device_map(model_id) requires a non-empty model_id.")
    model_id = model_id.strip()
    if model_id.lower().endswith(".json"):
        model_id = model_id[:-5]
    return model_id


def get_device_maps() -> List[str]:
    base = resources.files("cremalink.devices")
    models: List[str] = []
    for entry in base.iterdir():
        if entry.is_file() and entry.name.lower().endswith(".json"):
            models.append(Path(entry.name).stem)
    return sorted(set(models))


def device_map(model_id: str) -> str:
    model_id = _normalize_model_id(model_id)
    filename = f"{model_id}.json"

    base = resources.files("cremalink.devices")
    res: pathlib.Path = base.joinpath(filename)

    if not res.exists():
        available = get_device_maps()
        raise DeviceMapNotFoundError(
            f"Device map '{model_id}' not found. Available: {available}"
        )

    try:
        with resources.as_file(res) as p:
            return str(Path(p))
    except Exception:
        cache_dir = Path(tempfile.gettempdir()) / "cremalink_device_maps"
        cache_dir.mkdir(parents=True, exist_ok=True)
        target = cache_dir / filename

        target.write_bytes(res.read_bytes())
        return str(target)


def load_device_map(model_id: str) -> dict[str, Any]:
    path = device_map(model_id)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}
