"""
TLV codec for De'Longhi ECAM binary parameter encoding.

Each parameter is encoded as a tag byte followed by a value. Volume parameters
(coffee, milk, water) use 2-byte big-endian values; all others use 1-byte values.
"""
from __future__ import annotations

from typing import Optional

# Tags whose values are 2 bytes (big-endian); all others are 1 byte.
TWO_BYTE_PARAMS: frozenset[int] = frozenset({0x01, 0x09, 0x0F})

# Human-readable names for known parameter tags.
PARAM_NAMES: dict[int, str] = {
    0x01: "coffee_ml",
    0x02: "temperature",
    0x08: "double_shot",
    0x09: "milk_ml",
    0x0B: "foam_level",
    0x0C: "milk_first",
    0x0F: "water_ml",
    0x18: "pre_brew",
    0x19: "aroma",
    0x1B: "taste",
    0x1C: "milk_temp",
    0x1E: "recipe_type",
    0x20: "my_enabled",
    0x21: "my_level",
    0x23: "milk_circuit",
    0x24: "ice_amount",
    0x25: "cups_count",
    0x26: "batch_mode",
    0x27: "grinder",
}

# Reverse mapping: name -> tag.
PARAM_IDS: dict[str, int] = {v: k for k, v in PARAM_NAMES.items()}

# Canonical encoding order used by the machine firmware.
PARAM_ORDER: list[int] = [
    0x0B, 0x0C, 0x1C, 0x19, 0x01, 0x0F, 0x1B, 0x02, 0x08,
    0x18, 0x1E, 0x20, 0x21, 0x23, 0x24, 0x25, 0x26, 0x27, 0x09,
]


def parse_tlv_params(data: bytes) -> dict[int, int]:
    """
    Decode a TLV byte stream into a mapping of tag -> value.

    Args:
        data: Raw bytes containing concatenated TLV entries.

    Returns:
        A dict mapping integer parameter tags to integer values.
    """
    params: dict[int, int] = {}
    i = 0
    while i < len(data):
        tag = data[i]
        i += 1
        if tag in TWO_BYTE_PARAMS:
            if i + 1 < len(data):
                value = (data[i] << 8) | data[i + 1]
                i += 2
            else:
                break
        else:
            if i < len(data):
                value = data[i]
                i += 1
            else:
                break
        params[tag] = value
    return params


def encode_tlv_params(params: dict[int, int]) -> bytes:
    """
    Encode a tag -> value mapping into a TLV byte stream.

    Parameters are written in canonical order (see ``PARAM_ORDER``).
    Any tags not listed in ``PARAM_ORDER`` are appended at the end in
    ascending order.

    Args:
        params: Mapping of integer parameter tags to integer values.

    Returns:
        The encoded TLV bytes.
    """
    buf = bytearray()
    ordered = [t for t in PARAM_ORDER if t in params]
    ordered += sorted(t for t in params if t not in PARAM_ORDER)
    for tag in ordered:
        val = params[tag]
        if tag in TWO_BYTE_PARAMS:
            buf.extend([tag, (val >> 8) & 0xFF, val & 0xFF])
        else:
            buf.extend([tag, val & 0xFF])
    return bytes(buf)


def named_params(params: dict[int, int]) -> dict[str, int]:
    """
    Translate integer tag keys to human-readable names.

    Unknown tags are kept as hex strings (e.g. ``"0x2a"``).

    Args:
        params: Mapping of integer parameter tags to integer values.

    Returns:
        A dict mapping parameter names (or hex strings) to values.
    """
    return {
        PARAM_NAMES.get(tag, f"0x{tag:02x}"): val
        for tag, val in params.items()
    }
