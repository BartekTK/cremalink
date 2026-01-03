from __future__ import annotations

import time
from typing import Any, Optional

import requests

from cremalink.parsing.monitor.decode import build_monitor_snapshot
from cremalink.transports.base import DeviceTransport
from cremalink.resources import load_api_config

API_USER_AGENT = "datatransport/3.1.2 android/"
TOKEN_USER_AGENT = "DeLonghiComfort/3 CFNetwork/1568.300.101 Darwin/24.2.0"


class CloudTransport(DeviceTransport):
    def __init__(self, dsn: str, access_token: str, device_map_path: Optional[str] = None) -> None:
        self.api_conf = load_api_config()
        self.gigya_api = self.api_conf.get("GIGYA")
        self.ayla_api = self.api_conf.get("AYLA")

        self.dsn = dsn
        self.access_token = access_token
        self.device_map_path = device_map_path
        self.command_map: dict[str, Any] = {}
        self.property_map: dict[str, Any] = {}
        device = self._get(".json").get("device")
        self.id = device.get("key")
        self.model = device.get("model")
        self.is_lan_enabled = device.get("lan_enabled", False)
        self.type = device.get("type")
        self.is_online = device.get("connection_status", False) == "Online"
        self.ip = device.get("lan_ip")
        lan = self._get("/lan.json") or {}
        self.lan_key = lan.get("lanip", {}).get("lanip_key")

    def configure(self) -> None:
        return None

    # ---- helpers ----
    def _get(self, path: str):
        response = requests.get(
            url=f"{self.ayla_api.get('API_URL')}/dsns/{self.dsn}{path}",
            headers={
                "User-Agent": API_USER_AGENT,
                "Authorization": f"auth_token {self.access_token}",
                "Accept": "application/json",
            },
        )
        if response.status_code in [200, 201]:
            return response.json()
        raise ValueError(f"Cloud GET failed: {response.status_code} {response.text}")

    def _get_by_id(self, path: str):
        response = requests.get(
            url=f"{self.ayla_api.get('API_URL')}/devices/{self.id}{path}",
            headers={
                "User-Agent": API_USER_AGENT,
                "Authorization": f"auth_token {self.access_token}",
                "Accept": "application/json",
            },
        )
        if response.status_code in [200, 201]:
            return response.json()
        raise ValueError(f"Cloud GET failed: {response.status_code} {response.text}")

    def _post(self, path: str, data: dict):
        response = requests.post(
            url=f"{self.ayla_api.get('API_URL')}/dsns/{self.dsn}{path}",
            headers={
                "User-Agent": API_USER_AGENT,
                "Authorization": f"auth_token {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=data,
        )
        if response.status_code in [200, 201]:
            return response.json()
        raise ValueError(f"Cloud POST failed: {response.status_code} {response.text}")

    # ---- DeviceTransport ----
    def send_command(self, command: str) -> Any:
        return self._post(path="/properties/data_request/datapoints.json", data={"datapoint": {"value": command}})

    def set_mappings(self, command_map: dict[str, Any], property_map: dict[str, Any]) -> None:
        self.command_map = command_map
        self.property_map = property_map

    def get_properties(self) -> Any:
        return self._get("/properties.json")

    def get_property(self, name: str) -> Any:
        props = self._get(f"/properties.json?names[]={name}")
        if props:
            return props[0].get("property")
        return None

    def get_monitor(self) -> Any:
        property_name = self.property_map.get("monitor", "d302_monitor")
        prop = self.get_property(property_name) or {}
        raw_b64 = prop.get("value")
        received_at = prop.get("updated_at")
        try:
            received_ts = float(received_at) if received_at is not None else time.time()
        except (TypeError, ValueError):
            received_ts = time.time()
        payload = {
            "monitor": {"data": {"value": raw_b64}},
            "monitor_b64": raw_b64,
            "received_at": received_ts,
        }
        return build_monitor_snapshot(payload, source="cloud", device_id=self.dsn or self.id)

    def refresh_monitor(self) -> Any:
        return None

    def health(self) -> Any:
        return {"online": self.is_online}
