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


def test_get_counters():
    raw = {
        "c1": _make_prop("d705_tot_id1_espr", "948"),
        "c2": _make_prop("d706_tot_id2_coffee", "97"),
        "c3": _make_prop("d713_id10_flatwhite", "610"),
        "c4": _make_prop("d708_tot_id5_doppio_p", "642"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    counters = snapshot.get_counters()
    assert counters["espresso"] == 948
    assert counters["coffee"] == 97
    assert counters["flat_white"] == 610
    assert counters["doppio_plus"] == 642


def test_get_counters_skips_aggregates():
    """Aggregate counters without _id{N}_ should be ignored."""
    raw = {
        "c1": _make_prop("d701_tot_bev_b", "5000"),
        "c2": _make_prop("d731_tot_mug_hot", "100"),
        "c3": _make_prop("d705_tot_id1_espr", "948"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    counters = snapshot.get_counters()
    assert len(counters) == 1
    assert counters["espresso"] == 948


def test_get_counters_zero_values():
    raw = {
        "c1": _make_prop("d707_tot_id3_long", "0"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    counters = snapshot.get_counters()
    assert counters["long_coffee"] == 0


def test_get_counters_empty():
    raw = {}
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_counters() == {}


# ------------------------------------------------------------------
# Aggregate counters
# ------------------------------------------------------------------

def test_get_aggregate_counters():
    raw = {
        "c1": _make_prop("d701_tot_bev_b", "5000"),
        "c2": _make_prop("d731_tot_mug_hot", "100"),
        "c3": _make_prop("d704_tot_bev_all", "8000"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    agg = snapshot.get_aggregate_counters()
    assert agg["bev_b"] == 5000
    assert agg["mug_hot"] == 100
    assert agg["bev_all"] == 8000


def test_get_aggregate_counters_excludes_individual():
    """Individual beverage counters (with _id{N}_) should not appear."""
    raw = {
        "c1": _make_prop("d705_tot_id1_espr", "948"),
        "c2": _make_prop("d701_tot_bev_b", "5000"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    agg = snapshot.get_aggregate_counters()
    assert len(agg) == 1
    assert agg["bev_b"] == 5000


def test_get_aggregate_counters_empty():
    raw = {}
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_aggregate_counters() == {}


# ------------------------------------------------------------------
# Maintenance
# ------------------------------------------------------------------

def test_get_maintenance():
    raw = {
        "m1": _make_prop("d510_grounds_perc", "75"),
        "m2": _make_prop("d513_water_filter", "42"),
        "m3": _make_prop("d550_water_descale", "120"),
        "m4": _make_prop("d551_grounds_tot", "5100"),
        "m5": _make_prop("d553_total_water", "98000"),
        "m6": _make_prop("d556_hardness", "2"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    maint = snapshot.get_maintenance()
    assert maint["grounds_container"] == 75
    assert maint["water_filter"] == 42
    assert maint["water_since_descale"] == 120
    assert maint["grounds_count"] == 5100
    assert maint["total_water_dispensed"] == 98000
    assert maint["water_hardness_setting"] == 2


def test_get_maintenance_partial():
    raw = {
        "m1": _make_prop("d510_grounds_perc", "30"),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    maint = snapshot.get_maintenance()
    assert maint == {"grounds_container": 30}


def test_get_maintenance_empty():
    raw = {}
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_maintenance() == {}


# ------------------------------------------------------------------
# Helpers for D0 binary frame construction
# ------------------------------------------------------------------

def _build_d0_frame_b64(opcode_hi: int, opcode_lo: int, data: bytes) -> str:
    """Build a valid base64-encoded D0 frame with CRC."""
    payload = bytes([opcode_hi, opcode_lo]) + data
    frame_without_crc = bytes([0xD0, 2 + len(payload) + 2]) + payload
    crc = crc16_ccitt(frame_without_crc)
    return base64.b64encode(frame_without_crc + crc).decode()


# ------------------------------------------------------------------
# Favorites
# ------------------------------------------------------------------

def test_get_favorites():
    # Profile 1 favorites: espresso(0x01), doppio+(0x05), flat_white(0x0A)
    b64 = _build_d0_frame_b64(0xAC, 0xF0, bytes([0x01, 0x01, 0x05, 0x0A, 0x00, 0x00]))
    raw = {
        "f1": _make_prop("d265_fav_p1", b64),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    favs = snapshot.get_favorites()
    assert 1 in favs
    assert favs[1] == ["espresso", "doppio_plus", "flat_white"]


def test_get_favorites_multiple_profiles():
    b64_p1 = _build_d0_frame_b64(0xAC, 0xF0, bytes([0x01, 0x01, 0x07]))
    b64_p2 = _build_d0_frame_b64(0xAC, 0xF0, bytes([0x02, 0x0A, 0x06]))
    raw = {
        "f1": _make_prop("d265_fav_p1", b64_p1),
        "f2": _make_prop("d266_fav_p2", b64_p2),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    favs = snapshot.get_favorites()
    assert favs[1] == ["espresso", "cappuccino"]
    assert favs[2] == ["flat_white", "americano"]


def test_get_favorites_empty():
    raw = {}
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_favorites() == {}


# ------------------------------------------------------------------
# Recipe priority
# ------------------------------------------------------------------

def test_get_recipe_priority():
    # Profile 1: espresso(0x01), coffee(0x02), americano(0x06)
    b64 = _build_d0_frame_b64(0xA8, 0xF0, bytes([0x01, 0x01, 0x02, 0x06]))
    raw = {
        "r1": _make_prop("d261_priority_p1", b64),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    prio = snapshot.get_recipe_priority()
    assert prio[1] == ["espresso", "coffee", "americano"]


def test_get_recipe_priority_empty():
    raw = {}
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_recipe_priority() == {}


# ------------------------------------------------------------------
# Machine settings
# ------------------------------------------------------------------

def test_get_machine_settings():
    # d281 temperature: [00, 3D, 00, 00, 00, 02] → value=2
    b64_temp = _build_d0_frame_b64(0x95, 0x0F, bytes([0x00, 0x3D, 0x00, 0x00, 0x00, 0x02]))
    # d282 auto_off: [00, 3E, 00, 00, 00, 0x03] → value=3
    b64_auto = _build_d0_frame_b64(0x95, 0x0F, bytes([0x00, 0x3E, 0x00, 0x00, 0x00, 0x03]))
    # d283 water_hardness: [00, 32, 00, 00, 00, 00] → value=0
    b64_hard = _build_d0_frame_b64(0x95, 0x0F, bytes([0x00, 0x32, 0x00, 0x00, 0x00, 0x00]))
    raw = {
        "s1": _make_prop("d281_temperature", b64_temp),
        "s2": _make_prop("d282_auto_off", b64_auto),
        "s3": _make_prop("d283_water_hardness", b64_hard),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    settings = snapshot.get_machine_settings()
    assert settings["temperature"] == 2
    assert settings["auto_off"] == 3
    assert settings["water_hardness"] == 0


def test_get_machine_settings_partial():
    b64_temp = _build_d0_frame_b64(0x95, 0x0F, bytes([0x00, 0x3D, 0x00, 0x00, 0x00, 0x01]))
    raw = {
        "s1": _make_prop("d281_temp", b64_temp),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    settings = snapshot.get_machine_settings()
    assert settings == {"temperature": 1}


def test_get_machine_settings_empty():
    raw = {}
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_machine_settings() == {}


# ------------------------------------------------------------------
# Active profile
# ------------------------------------------------------------------

def test_get_active_profile():
    # d286: opcode 0x95F0, profile=3, value=0xEE
    b64 = _build_d0_frame_b64(0x95, 0xF0, bytes([0x03, 0xEE]))
    raw = {
        "a1": _make_prop("d286_active_profile", b64),
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_active_profile() == 3


def test_get_active_profile_none():
    raw = {}
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get_active_profile() is None
