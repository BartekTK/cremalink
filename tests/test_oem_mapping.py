"""Tests for OEM model mapping and device map resolution."""
import pytest

from cremalink.devices import (
    DeviceMapNotFoundError,
    OEM_MODEL_MAP,
    device_map,
    load_device_map,
    resolve_model_id,
)


def test_resolve_known_oem_model():
    assert resolve_model_id("DL-striker-cb") == "ECAM450"


def test_resolve_known_esp_module():
    assert resolve_model_id("AY008ESP1") == "ECAM450"


def test_resolve_unknown_passthrough():
    assert resolve_model_id("ECAM452") == "ECAM452"
    assert resolve_model_id("some_random_model") == "some_random_model"


def test_device_map_oem_model():
    """device_map() should resolve OEM model to ECAM450.json path."""
    path = device_map("DL-striker-cb")
    assert "ECAM450" in path
    assert path.endswith(".json")


def test_device_map_direct():
    """Direct model IDs should still work."""
    path = device_map("ECAM450")
    assert "ECAM450" in path


def test_device_map_not_found():
    with pytest.raises(DeviceMapNotFoundError):
        device_map("NONEXISTENT_MODEL_999")


def test_load_device_map_oem():
    data = load_device_map("DL-striker-cb")
    assert data["device_type"] == "ECAM450"
    assert "command_map" in data
    assert "espresso" in data["command_map"]


def test_oem_model_map_entries():
    assert "DL-striker-cb" in OEM_MODEL_MAP
    assert "AY008ESP1" in OEM_MODEL_MAP
