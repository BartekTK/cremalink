"""
Decoder for base64-encoded ECAM recipe property values.

Recipes are stored in the Ayla cloud as base64 strings encoding a binary frame
with a 0xD0 marker, a command word (0xA6F0 for profile, 0xB0F0 for defaults),
TLV parameters, and a CRC-16 checksum.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Optional

from cremalink.core.binary import crc16_ccitt
from cremalink.parsing.tlv import parse_tlv_params, named_params


@dataclass(frozen=True)
class RecipeSnapshot:
    """
    A decoded recipe from a cloud property value.

    Attributes:
        format: One of ``"profile"``, ``"default"``, or ``"unknown"``.
        bev_id: The numeric beverage ID.
        profile: The profile number (1-4), or ``None`` for default recipes.
        params: Raw tag -> value mapping from TLV decoding.
        named_params: Human-readable parameter names.
        crc_ok: Whether the CRC-16 checksum validated.
        raw_hex: The full raw frame as a hex string.
    """
    format: str
    bev_id: int
    profile: Optional[int] = None
    params: dict[int, int] = field(default_factory=dict)
    named_params: dict[str, int] = field(default_factory=dict)
    crc_ok: bool = False
    raw_hex: str = ""


def decode_recipe_b64(b64_str: str) -> Optional[RecipeSnapshot]:
    """
    Decode a single base64-encoded recipe string.

    Args:
        b64_str: The base64 string from a cloud property value.

    Returns:
        A ``RecipeSnapshot`` if the data is a valid recipe frame,
        otherwise ``None``.
    """
    try:
        raw = base64.b64decode(b64_str)
    except Exception:
        return None

    if len(raw) < 6:
        return None

    marker = raw[0]
    if marker != 0xD0:
        return None

    length = raw[1]
    frame_end = min(length + 1, len(raw))

    crc_bytes = raw[frame_end - 2:frame_end]
    crc_check = crc16_ccitt(raw[:frame_end - 2])

    cmd = (raw[2] << 8) | raw[3]

    if cmd == 0xA6F0:
        # Profile recipe: D0 [len] A6 F0 [profile] [bev_id] [TLV...] [CRC]
        profile = raw[4]
        bev_id = raw[5]
        param_bytes = raw[6:frame_end - 2]
        params = parse_tlv_params(param_bytes)
        return RecipeSnapshot(
            format="profile",
            bev_id=bev_id,
            profile=profile,
            params=params,
            named_params=named_params(params),
            crc_ok=crc_check == crc_bytes,
            raw_hex=raw.hex(),
        )
    elif cmd == 0xB0F0:
        # Default recipe: D0 [len] B0 F0 [bev_id] [TLV...] [CRC]
        bev_id = raw[4]
        return RecipeSnapshot(
            format="default",
            bev_id=bev_id,
            crc_ok=crc_check == crc_bytes,
            raw_hex=raw.hex(),
        )
    else:
        return RecipeSnapshot(
            format="unknown",
            bev_id=0,
            raw_hex=raw.hex(),
        )


def decode_recipe_container(json_str: str) -> list[RecipeSnapshot]:
    """
    Decode a JSON container of recipes (used in default recipe properties).

    Default recipe properties (d002-d008) store a JSON object where each
    value is a base64-encoded recipe string.

    Args:
        json_str: The JSON string from a cloud property value.

    Returns:
        A list of successfully decoded ``RecipeSnapshot`` objects.
    """
    try:
        container = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(container, dict):
        return []

    results: list[RecipeSnapshot] = []
    for b64_val in container.values():
        if not isinstance(b64_val, str):
            continue
        snapshot = decode_recipe_b64(b64_val)
        if snapshot is not None:
            results.append(snapshot)
    return results
