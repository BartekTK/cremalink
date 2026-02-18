"""
Command frame builder for ECAM brew and stop commands.

Constructs complete command frames with the structure:
``[0x0D] [length] [0x83 0xF0] [bev_id] [trigger] [TLV params] [CRC16]``
"""
from __future__ import annotations

from cremalink.core.binary import crc16_ccitt
from cremalink.parsing.tlv import encode_tlv_params

# Frame markers and opcodes.
COMMAND_MARKER = 0x0D
BREW_OPCODE_HI = 0x83
BREW_OPCODE_LO = 0xF0

# Trigger bytes.
TRIGGER_START = 0x01
TRIGGER_STOP = 0x02


def build_brew_command(
    bev_id: int,
    params: dict[int, int],
    trigger: int = TRIGGER_START,
) -> str:
    """
    Build a complete brew command frame as a hex string.

    Args:
        bev_id: The numeric beverage ID.
        params: TLV parameter tag -> value mapping.
        trigger: The trigger byte (``0x01`` for start, ``0x02`` for stop).

    Returns:
        The complete command frame as a hexadecimal string, ready for
        ``Device.send_command()``.
    """
    tlv_bytes = encode_tlv_params(params)
    payload = bytes([BREW_OPCODE_HI, BREW_OPCODE_LO, bev_id, trigger]) + tlv_bytes

    # Frame: marker + length + payload + CRC
    frame_len = 1 + 1 + len(payload) + 2  # marker + length_byte + payload + crc
    frame_without_crc = bytes([COMMAND_MARKER, frame_len]) + payload
    checksum = crc16_ccitt(frame_without_crc)
    return (frame_without_crc + checksum).hex()


def build_stop_command(bev_id: int = 0x10) -> str:
    """
    Build a universal stop command frame as a hex string.

    Args:
        bev_id: The beverage ID to stop (default ``0x10``).

    Returns:
        The complete stop command frame as a hexadecimal string.
    """
    return build_brew_command(
        bev_id=bev_id,
        params={0x0F: 250, 0x1B: 1},
        trigger=TRIGGER_STOP,
    )
