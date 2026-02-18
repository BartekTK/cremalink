"""Tests for recipe decoding from cloud property values."""
import base64
import json

import pytest

from cremalink.core.binary import crc16_ccitt
from cremalink.parsing.recipes import RecipeSnapshot, decode_recipe_b64, decode_recipe_container


def _build_profile_recipe(profile: int, bev_id: int, tlv: bytes) -> str:
    """Helper: build a valid profile recipe base64 string."""
    # D0 [len] A6 F0 [profile] [bev_id] [TLV...] [CRC]
    payload = bytes([0xA6, 0xF0, profile, bev_id]) + tlv
    frame_without_crc = bytes([0xD0, 2 + len(payload) + 2]) + payload
    crc = crc16_ccitt(frame_without_crc)
    return base64.b64encode(frame_without_crc + crc).decode()


def _build_default_recipe(bev_id: int, raw_params: bytes = b"\x01\x00") -> str:
    """Helper: build a valid default recipe base64 string."""
    # D0 [len] B0 F0 [bev_id] [params...] [CRC]
    payload = bytes([0xB0, 0xF0, bev_id]) + raw_params
    frame_without_crc = bytes([0xD0, 2 + len(payload) + 2]) + payload
    crc = crc16_ccitt(frame_without_crc)
    return base64.b64encode(frame_without_crc + crc).decode()


def test_decode_profile_recipe():
    # Profile 1, espresso (0x01), coffee_ml=36, taste=4, temperature=2
    tlv = bytes([0x01, 0x00, 0x24, 0x1B, 0x04, 0x02, 0x05])
    b64 = _build_profile_recipe(1, 0x01, tlv)
    result = decode_recipe_b64(b64)
    assert result is not None
    assert result.format == "profile"
    assert result.bev_id == 0x01
    assert result.profile == 1
    assert result.params[0x01] == 36
    assert result.params[0x1B] == 4
    assert result.params[0x02] == 5
    assert result.crc_ok is True
    assert result.named_params["coffee_ml"] == 36


def test_decode_default_recipe():
    b64 = _build_default_recipe(0x01)
    result = decode_recipe_b64(b64)
    assert result is not None
    assert result.format == "default"
    assert result.bev_id == 0x01
    assert result.crc_ok is True


def test_decode_invalid_base64():
    result = decode_recipe_b64("not-valid-base64!!!")
    assert result is None


def test_decode_too_short():
    b64 = base64.b64encode(b"\xd0\x01").decode()
    result = decode_recipe_b64(b64)
    assert result is None


def test_decode_wrong_marker():
    # Not 0xD0 marker
    b64 = base64.b64encode(b"\x0d\x06\xa6\xf0\x01\x01\x00\x00").decode()
    result = decode_recipe_b64(b64)
    assert result is None


def test_decode_unknown_command():
    # D0 [len] FF FF ... -> unknown format
    payload = bytes([0xFF, 0xFF, 0x01])
    frame_without_crc = bytes([0xD0, 2 + len(payload) + 2]) + payload
    crc = crc16_ccitt(frame_without_crc)
    b64 = base64.b64encode(frame_without_crc + crc).decode()
    result = decode_recipe_b64(b64)
    assert result is not None
    assert result.format == "unknown"


def test_decode_corrupted_crc():
    # Build valid recipe, then flip a CRC byte
    tlv = bytes([0x01, 0x00, 0x24])
    b64_good = _build_profile_recipe(1, 0x01, tlv)
    raw = bytearray(base64.b64decode(b64_good))
    raw[-1] ^= 0xFF  # Corrupt last byte (CRC)
    b64_bad = base64.b64encode(raw).decode()
    result = decode_recipe_b64(b64_bad)
    assert result is not None
    assert result.crc_ok is False


def test_decode_recipe_container():
    b64_1 = _build_default_recipe(0x01)
    b64_2 = _build_default_recipe(0x02)
    container = json.dumps({"rec1": b64_1, "rec2": b64_2})
    results = decode_recipe_container(container)
    assert len(results) == 2
    assert all(r.format == "default" for r in results)


def test_decode_recipe_container_invalid_json():
    results = decode_recipe_container("not json at all")
    assert results == []


def test_decode_recipe_container_non_dict():
    results = decode_recipe_container(json.dumps([1, 2, 3]))
    assert results == []


def test_decode_recipe_container_mixed():
    b64_good = _build_default_recipe(0x01)
    container = json.dumps({"good": b64_good, "bad": "not-base64!!!", "num": 42})
    results = decode_recipe_container(container)
    # Only the valid one should be returned
    assert len(results) == 1


def test_recipe_snapshot_is_frozen():
    snapshot = RecipeSnapshot(format="profile", bev_id=1)
    try:
        snapshot.bev_id = 99
        assert False, "Should not allow mutation"
    except AttributeError:
        pass
