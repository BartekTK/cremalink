from unittest.mock import patch

from cremalink.core.binary import hex_to_signed_decimal
from cremalink.domain.device import APP_ID_HEX, Device


class AppConnectionTransport:
    def __init__(self, app_id_values):
        self._app_id_values = list(app_id_values)
        self.calls = []

    def configure(self):
        return None

    def send_command(self, command: str, alternative_property: str = None):
        self.calls.append({"command": command, "property": alternative_property})
        return {}

    def set_mappings(self, command_map, property_map):
        return None

    def get_monitor(self):
        return None

    def refresh_monitor(self):
        return None

    def get_properties(self):
        return {}

    def get_property(self, name: str):
        if len(self._app_id_values) > 1:
            value = self._app_id_values.pop(0)
        else:
            value = self._app_id_values[0]
        return {"name": name, "value": value}

    def health(self):
        return {}


def test_ensure_app_connection_registers_once_within_interval():
    transport = AppConnectionTransport(["0", hex_to_signed_decimal(APP_ID_HEX)])
    device = Device(
        transport=transport,
        property_map={
            "app_id": "app_id",
            "device_connected": "app_device_connected",
        },
        command_map={"refresh": {"command": "AA"}},
    )

    with patch("cremalink.domain.device.time.sleep", return_value=None), patch(
        "cremalink.domain.device.time.monotonic",
        side_effect=[10.0, 20.0],
    ):
        assert device.ensure_app_connection(refresh_interval=60) is True
        assert device.ensure_app_connection(refresh_interval=60) is True

    assert len(transport.calls) == 1
    assert transport.calls[0]["property"] == "app_device_connected"


def test_ensure_app_connection_refreshes_after_interval():
    transport = AppConnectionTransport([hex_to_signed_decimal(APP_ID_HEX)])
    device = Device(
        transport=transport,
        property_map={"app_id": "app_id"},
        command_map={"refresh": {"command": "AA"}},
    )
    device._app_connection_active = True
    device._last_app_connection_refresh = 0.0

    with patch(
        "cremalink.domain.device.time.monotonic",
        side_effect=[120.0, 121.0],
    ):
        assert device.ensure_app_connection(refresh_interval=60) is True

    assert len(transport.calls) == 1
    assert transport.calls[0]["property"] is None
