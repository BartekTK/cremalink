from typing import Optional

import httpx

from cremalink.local_server_app.config import ServerSettings
from cremalink.local_server_app.state import LocalServerState


class DeviceAdapter:
    def __init__(self, settings: ServerSettings, logger):
        self.settings = settings
        self.logger = logger
        self._client: Optional[httpx.AsyncClient] = None

    async def _client_instance(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.settings.device_register_timeout,
                verify=self.settings.device_register_ca_path or self.settings.device_register_verify,
            )
        return self._client

    async def register_with_device(self, state: LocalServerState) -> None:
        if not self.settings.enable_device_register:
            self.logger.info("register_skipped", extra={"details": {"reason": "disabled"}})
            return
        if not state.device_ip:
            raise ValueError("Device IP not configured")
        api_url = f"{state.device_scheme}://{state.device_ip}/local_reg.json"
        payload = {
            "local_reg": {
                "ip": self.settings.server_ip,
                "notify": 1,
                "port": self.settings.server_port,
                "uri": "/local_lan",
            }
        }
        client = await self._client_instance()
        try:
            resp = await client.put(api_url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            await state.set_registered(False)
            state.log("local_reg_failed", {"error": str(exc)})
            raise ConnectionError(f"local_reg failed: {exc}") from exc
        else:
            await state.set_registered(True)
            state.log("local_reg_ok", {"device_ip": state.device_ip, "scheme": state.device_scheme})

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
