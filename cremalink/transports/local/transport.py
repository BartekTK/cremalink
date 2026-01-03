from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

import requests

from cremalink.parsing.monitor.decode import build_monitor_snapshot
from cremalink.parsing.properties.decode import PropertiesSnapshot
from cremalink.transports.base import DeviceTransport


class LocalTransport(DeviceTransport):
    def __init__(
        self,
        dsn: str,
        lan_key: str,
        device_ip: Optional[str],
        server_host: str = "127.0.0.1",
        server_port: int = 10280,
        device_scheme: str = "http",
        auto_configure: bool = False,
        command_map: Optional[dict[str, Any]] = None,
        property_map: Optional[dict[str, Any]] = None,
    ) -> None:
        self.dsn = dsn
        self.lan_key = lan_key
        self.device_ip = device_ip
        self.device_scheme = device_scheme
        self.server_base_url = f"http://{server_host}:{server_port}"
        self._configured = False
        self.command_map = command_map or {}
        self.property_map = property_map or {}
        self._auto_configure = auto_configure
        if auto_configure:
            self.configure()

    # ---- helpers ----
    def _post_server(self, path: str, body: dict, timeout: int = 10) -> requests.Response:
        return requests.post(
            url=f"{self.server_base_url}{path}",
            headers={"Content-Type": "application/json"},
            json=body,
            timeout=timeout,
        )

    def _get_server(self, path: str, timeout: int = 10) -> requests.Response:
        return requests.get(f"{self.server_base_url}{path}", timeout=timeout)

    # ---- DeviceTransport ----
    def configure(self) -> None:
        payload = {
            "dsn": self.dsn,
            "device_ip": self.device_ip,
            "lan_key": self.lan_key,
            "device_scheme": self.device_scheme,
            "monitor_property_name": self.property_map.get("monitor", "d302_monitor"),
        }
        try:
            resp = self._post_server("/configure", payload)
        except requests.RequestException as exc:
            raise ConnectionError(
                f"Could not reach local server at {self.server_base_url} during configure. "
                f"Start the server (python -m cremalink.local_server) or adjust server_host/server_port. "
                f"Original error: {exc}"
            ) from exc
        if resp.status_code not in (200, 201):
            raise ValueError(f"Failed to configure server: {resp.status_code} {resp.text}")
        self._configured = True

    def send_command(self, command: str) -> dict[str, Any]:
        if not self._configured:
            self.configure()
        resp = self._post_server("/command", {"command": command})
        if resp.status_code not in (200, 201):
            raise ValueError(f"Failed to send command to server: {resp.status_code} {resp.text}")
        return resp.json()

    def get_properties(self) -> PropertiesSnapshot:
        resp = self._get_server("/get_properties")
        if resp.status_code != 200:
            raise ValueError(f"Failed to get properties from server: {resp.status_code} {resp.text}")
        payload = resp.json()
        received = payload.get("received_at")
        received_dt = None
        if received is not None:
            try:
                received_dt = datetime.fromtimestamp(received)
            except Exception:
                received_dt = None
        return PropertiesSnapshot(raw=payload.get("properties", payload), received_at=received_dt)

    def get_property(self, name: str) -> Any:
        snapshot = self.get_properties()
        value = snapshot.get(name)
        if value is None:
            resp = self._get_server(f"/properties/{name}")
            if resp.status_code == 200:
                return resp.json().get("value")
            raise ValueError(f"Failed to get property '{name}' from server: {resp.status_code} {resp.text}")
        return value

    def get_monitor(self) -> Any:
        resp = self._get_server("/get_monitor")
        if resp.status_code != 200:
            raise ValueError(f"Failed to get monitor from server: {resp.status_code} {resp.text}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ValueError(f"Failed to parse monitor payload: {resp.text}") from exc
        return build_monitor_snapshot(payload, source="local", device_id=self.dsn)

    def refresh_monitor(self) -> None:
        resp = self._get_server("/refresh_monitor")
        if resp.status_code != 200:
            raise ValueError(f"Failed to refresh monitor: {resp.status_code} {resp.text}")

    def health(self) -> str:
        return self._get_server("/health").text

    def set_mappings(self, command_map: dict[str, Any], property_map: dict[str, Any]) -> None:
        previous_monitor = self.property_map.get("monitor", "d302_monitor")
        self.command_map = command_map
        self.property_map = property_map
        updated_monitor = self.property_map.get("monitor", "d302_monitor")
        if self._auto_configure and (not self._configured or previous_monitor != updated_monitor):
            self.configure()
