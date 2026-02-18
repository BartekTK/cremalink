"""Tests for enhanced PropertiesSnapshot: recipes, counters, profile names."""
import base64
import datetime as dt
import json

from cremalink.core.binary import crc16_ccitt
from cremalink.parsing.properties.decode import PropertiesSnapshot


def _build_profile_recipe_b64(profile: int, bev_id: int, tlv: bytes) -> str:
    """Helper: build a valid profile recipe base64 string."""
    payload = bytes([0xA6, 0xF0, profile, bev_id]) + tlv
    frame_without_crc = bytes([0xD0, 2 + len(payload) + 2]) + payload
    crc = crc16_ccitt(frame_without_crc)
    return base64.b64encode(frame_without_crc + crc).decode()


def _make_prop(name: str, value) -> dict:
    """Helper: wrap name/value into the standard property structure."""
    return {"property": {"name": name, "value": value}}


def test_get_recipes_profile():
    b64 = _build_profile_recipe_b64(1, 0x01, bytes([0x01, 0x00, 0x24]))
    raw = {
        "p1": _make_prop("d059_rec_espresso", b64),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    recipes = snapshot.get_recipes()
    assert len(recipes) == 1
    assert recipes[0].format == "profile"
    assert recipes[0].bev_id == 0x01


def test_get_recipes_filter_by_profile():
    b64_p1 = _build_profile_recipe_b64(1, 0x01, bytes([0x01, 0x00, 0x24]))
    b64_p2 = _build_profile_recipe_b64(2, 0x01, bytes([0x01, 0x00, 0x30]))
    raw = {
        "p1": _make_prop("d059_rec_espresso_p1", b64_p1),
        "p2": _make_prop("d060_rec_espresso_p2", b64_p2),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))

    p1_recipes = snapshot.get_recipes(profile=1)
    assert len(p1_recipes) == 1
    assert p1_recipes[0].profile == 1

    p2_recipes = snapshot.get_recipes(profile=2)
    assert len(p2_recipes) == 1
    assert p2_recipes[0].profile == 2


def test_get_recipes_ignores_non_recipe():
    raw = {
        "p1": _make_prop("d250_beans_type", "2"),
        "p2": _make_prop("d302_monitor_machine", "AAAA"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_recipes() == []


def test_get_recipes_json_container():
    # Build a default recipe container
    payload = bytes([0xB0, 0xF0, 0x01]) + b"\x01\x00"
    frame_without_crc = bytes([0xD0, 2 + len(payload) + 2]) + payload
    crc = crc16_ccitt(frame_without_crc)
    b64_default = base64.b64encode(frame_without_crc + crc).decode()

    container_json = json.dumps({"espresso": b64_default})
    raw = {
        "p1": _make_prop("d002_rec_defaults", container_json),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    recipes = snapshot.get_recipes()
    assert len(recipes) == 1
    assert recipes[0].format == "default"


def test_get_profile_names():
    raw = {
        "p1": _make_prop("d051", "Bartek"),
        "p2": _make_prop("d052", "Anita"),
        "p3": _make_prop("d053", "Explorer 3"),
        "p4": _make_prop("d054", "Explorer 4"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    names = snapshot.get_profile_names()
    assert names == {1: "Bartek", 2: "Anita", 3: "Explorer 3", 4: "Explorer 4"}


def test_get_profile_names_partial():
    raw = {
        "p1": _make_prop("d051", "Alice"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    names = snapshot.get_profile_names()
    assert names == {1: "Alice"}


def test_get_profile_names_empty():
    raw = {}
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_profile_names() == {}
