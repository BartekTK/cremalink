from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any


@lru_cache
def load_api_config() -> dict[str, Any]:
    resource = resources.files("cremalink.resources").joinpath("api_config.json")
    with resource.open("r", encoding="utf-8") as f:
        return json.load(f)
