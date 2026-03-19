"""
This module provides the `CloudTransport` class, which handles communication
with a coffee machine via the manufacturer's cloud API (Ayla Networks).
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import requests

from cremalink.clients.ayla import API_USER_AGENT, DEFAULT_REQUEST_TIMEOUT
from cremalink.parsing.monitor.decode import build_monitor_snapshot
from cremalink.parsing.properties import PropertiesSnapshot
from cremalink.transports.base import DeviceTransport
from cremalink.resources import load_api_config

if TYPE_CHECKING:
    from cremalink.clients.ayla import AylaSession


class CloudTransport(DeviceTransport):
    """
    A transport for communicating with a device via the cloud API.

    This transport interacts directly with the Ayla cloud service endpoints,
    using a short-lived access token for authentication. Upon initialization,
    it fetches key device metadata from the cloud and stores it.
    """

    def __init__(
        self,
        dsn: str,
        access_token: Optional[str] = None,
        device_map_path: Optional[str] = None,
        ayla_session: Optional["AylaSession"] = None,
    ) -> None:
        """
        Initializes the CloudTransport.

        Args:
            dsn: The Device Serial Number.
            access_token: A valid OAuth access token for the cloud API.
            device_map_path: Optional path to a device-specific command map file.
            ayla_session: Shared Ayla session capable of refreshing expired tokens.
        """
        self.api_conf = load_api_config()
        self.gigya_api = self.api_conf.get("GIGYA")
        self.ayla_api = self.api_conf.get("AYLA")

        if ayla_session is None and not access_token:
            raise ValueError("Either access_token or ayla_session must be provided")

        self.dsn = dsn
        self.access_token = access_token
        self.ayla_session = ayla_session
        self.device_map_path = device_map_path
        self.command_map: dict[str, Any] = {}
        self.property_map: dict[str, Any] = {}

        # Fetch device metadata from the cloud immediately upon initialization.
        device = self._get(".json").get("device", {})
        self.id = device.get("key")  # The Ayla internal device ID
        self.model = device.get("model")
        self.is_lan_enabled = device.get("lan_enabled", False)
        self.type = device.get("type")
        self.is_online = device.get("connection_status", False) == "Online"
        self.ip = device.get("lan_ip")

        # Fetch LAN key, which might be needed for other operations.
        try:
            lan = self._get("/lan.json") or {}
            self.lan_key = lan.get("lanip", {}).get("lanip_key")
        except requests.HTTPError:
            self.lan_key = None

    def configure(self) -> None:
        """Configuration is handled during __init__, so this is a no-op."""
        return None

    # ---- helpers ----
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Make an authenticated Ayla request.

        When a shared session is available, it will transparently refresh an
        expired access token and retry once.
        """
        if self.ayla_session is not None:
            return self.ayla_session.request(
                method,
                path,
                params=params,
                json_body=json_body,
            )

        response = requests.request(
            method=method,
            url=f"{self.ayla_api.get('API_URL')}{path}",
            headers={
                "User-Agent": API_USER_AGENT,
                "Authorization": f"auth_token {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            params=params,
            json=json_body,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response

    def _get(self, path: str) -> dict:
        """Helper for making authenticated GET requests using the device DSN."""
        response = self._request("GET", f"/dsns/{self.dsn}{path}")
        return response.json()

    def _get_by_id(self, path: str) -> dict:
        """Helper for making authenticated GET requests using the internal device ID."""
        response = self._request("GET", f"/devices/{self.id}{path}")
        return response.json()

    def _post(self, path: str, data: dict) -> dict:
        """Helper for making authenticated POST requests."""
        response = self._request("POST", f"/dsns/{self.dsn}{path}", json_body=data)
        return response.json()

    # ---- DeviceTransport Implementation ----
    def send_command(self, command: str, alternative_property: str = None) -> Any:
        """Sends a command to the device by creating a new 'datapoint' via the cloud API."""
        payload = {"datapoint": {"value": command}}
        data_request = alternative_property or self.property_map.get("data_request")
        return self._post(path=f"/properties/{data_request}/datapoints.json", data=payload)

    def set_mappings(self, command_map: dict[str, Any], property_map: dict[str, Any]) -> None:
        """Stores the provided command and property maps on the instance."""
        self.command_map = command_map
        self.property_map = property_map

    def get_properties(self) -> PropertiesSnapshot:
        """Fetches all properties for the device from the cloud API.

        The Ayla API returns a list of ``{"property": {...}}`` objects.
        This method converts that list into a dict keyed by property name
        and wraps it in a :class:`PropertiesSnapshot`.
        """
        raw = self._get("/properties.json")
        props_dict: dict[str, Any] = {}
        items = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
        for item in items:
            name = item.get("property", {}).get("name", "")
            if name:
                props_dict[name] = item
        return PropertiesSnapshot(raw=props_dict, received_at=datetime.now())

    def get_property(self, name: str) -> Any:
        """Fetches a single, specific property by name."""
        props = self._request(
            "GET",
            f"/dsns/{self.dsn}/properties.json",
            params={"names[]": name},
        ).json()
        # The API returns a list, even for a single property.
        if props and isinstance(props, list):
            return props[0].get("property")
        return None

    def get_monitor(self) -> Any:
        """
        Fetches, parses, and returns the device's monitoring status.

        This works by fetching the specific 'monitor' property, extracting its
        base64 value, and then decoding it into a structured snapshot.
        """
        property_name = self.property_map.get("monitor")
        prop = self.get_property(property_name) or {}
        raw_b64 = prop.get("value")
        received_at = prop.get("updated_at")

        try:
            # Convert timestamp string to float if possible, otherwise use current time.
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
        """
        The cloud API does not provide a direct way to force a monitor refresh.
        This method is a no-op.
        """
        return None

    def health(self) -> Any:
        """
        Returns the device's online status as determined during initialization.
        This does not perform a live health check.
        """
        return {"online": self.is_online}
