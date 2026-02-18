"""Tests for command frame builder."""
import json

from cremalink.core.binary import crc16_ccitt
from cremalink.parsing.commands import (
    build_brew_command,
    build_stop_command,
    COMMAND_MARKER,
    BREW_OPCODE_HI,
    BREW_OPCODE_LO,
    TRIGGER_START,
    TRIGGER_STOP,
)
from cremalink.parsing.tlv import parse_tlv_params
from cremalink.devices import load_device_map


def test_build_simple_command():
    # Build espresso with just coffee_ml=36, taste=4, temp=2
    params = {0x01: 36, 0x1B: 4, 0x02: 5}
    hex_cmd = build_brew_command(0x01, params)

    # Verify frame structure
    frame = bytes.fromhex(hex_cmd)
    assert frame[0] == COMMAND_MARKER
    assert frame[2] == BREW_OPCODE_HI
    assert frame[3] == BREW_OPCODE_LO
    assert frame[4] == 0x01  # bev_id
    assert frame[5] == TRIGGER_START


def test_command_crc_valid():
    params = {0x01: 100, 0x1B: 3}
    hex_cmd = build_brew_command(0x02, params)
    frame = bytes.fromhex(hex_cmd)

    # CRC is last 2 bytes, covers everything before it
    frame_without_crc = frame[:-2]
    expected_crc = crc16_ccitt(frame_without_crc)
    assert frame[-2:] == expected_crc


def test_command_length_byte():
    params = {0x01: 100}
    hex_cmd = build_brew_command(0x01, params)
    frame = bytes.fromhex(hex_cmd)

    # Length byte should equal total frame length
    assert frame[1] == len(frame)


def test_stop_command():
    hex_cmd = build_stop_command()
    frame = bytes.fromhex(hex_cmd)

    assert frame[0] == COMMAND_MARKER
    assert frame[4] == 0x10  # default stop bev_id
    assert frame[5] == TRIGGER_STOP

    # Verify CRC
    expected_crc = crc16_ccitt(frame[:-2])
    assert frame[-2:] == expected_crc


def test_stop_command_custom_bev_id():
    hex_cmd = build_stop_command(bev_id=0x01)
    frame = bytes.fromhex(hex_cmd)
    assert frame[4] == 0x01


def test_roundtrip_params():
    original_params = {0x01: 200, 0x09: 150, 0x0F: 100, 0x1B: 3, 0x02: 5}
    hex_cmd = build_brew_command(0x06, original_params)
    frame = bytes.fromhex(hex_cmd)

    # Extract TLV from frame: after marker(1) + len(1) + opcode(2) + bev(1) + trigger(1)
    tlv_start = 6
    tlv_end = len(frame) - 2  # before CRC
    decoded = parse_tlv_params(frame[tlv_start:tlv_end])
    assert decoded == original_params


def test_command_matches_ecam450_espresso():
    """Verify our builder produces a valid command matching ECAM450.json format."""
    device_data = load_device_map("ECAM450")
    stored_hex = device_data["command_map"]["espresso"]["command"]
    stored_frame = bytes.fromhex(stored_hex)

    # Extract params from the stored command
    tlv_start = 6
    tlv_end = len(stored_frame) - 2
    stored_params = parse_tlv_params(stored_frame[tlv_start:tlv_end])
    stored_bev_id = stored_frame[4]

    # Rebuild the command
    rebuilt_hex = build_brew_command(stored_bev_id, stored_params)

    # The rebuilt command should exactly match the stored one
    assert rebuilt_hex == stored_hex


def test_command_matches_ecam450_cappuccino():
    """Verify round-trip for a milk drink command."""
    device_data = load_device_map("ECAM450")
    stored_hex = device_data["command_map"]["cappuccino"]["command"]
    stored_frame = bytes.fromhex(stored_hex)

    stored_params = parse_tlv_params(stored_frame[6:-2])
    stored_bev_id = stored_frame[4]

    rebuilt_hex = build_brew_command(stored_bev_id, stored_params)
    assert rebuilt_hex == stored_hex


def test_empty_params():
    hex_cmd = build_brew_command(0x01, {})
    frame = bytes.fromhex(hex_cmd)
    # marker(1) + len(1) + opcode(2) + bev(1) + trigger(1) + crc(2) = 8
    assert len(frame) == 8
    assert crc16_ccitt(frame[:-2]) == frame[-2:]
