from __future__ import annotations

import base64
from typing import Iterable


CRC16_POLY = 0x1021


def crc16_ccitt(data: bytes) -> bytes:
    crc = 0x1D0F
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ CRC16_POLY
            else:
                crc <<= 1
    return (crc & 0xFFFF).to_bytes(2, byteorder="big")


def b64_to_cmd_hex(b64_data: str) -> str:
    cleaned = "".join(b64_data.split())
    cleaned += "=" * (-len(cleaned) % 4)
    raw = base64.b64decode(cleaned)
    length = raw[1]
    cmd_frame = raw[: length + 1]
    return cmd_frame.hex()


def get_bit(byte_value: int, bit_index: int) -> bool:
    if bit_index < 0 or bit_index > 7:
        raise ValueError("bit_index must be between 0 and 7")
    return bool(byte_value & (1 << bit_index))


def safe_byte_at(data: Iterable[int] | bytes, index: int) -> int | None:
    try:
        return list(data)[index]
    except (IndexError, TypeError):
        return None
