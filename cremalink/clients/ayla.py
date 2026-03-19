from __future__ import annotations

import json
import os
from typing import Any

import requests

from cremalink.resources import load_api_config

API_USER_AGENT = "datatransport/3.1.2 android/"
TOKEN_USER_AGENT = "DeLonghiComfort/3 CFNetwork/1568.300.101 Darwin/24.2.0"
DEFAULT_REQUEST_TIMEOUT = 10


class AylaSession:
    """Authenticated session wrapper for Ayla API calls.

    The session owns refresh-token persistence and can transparently refresh
    the short-lived access token when the API responds with ``401``.
    """

    def __init__(self, token_path: str, timeout: float = DEFAULT_REQUEST_TIMEOUT):
        if not token_path.endswith(".json"):
            raise ValueError("token_path must point to a .json file")

        self.token_path = token_path
        self.timeout = timeout
        self.api_conf = load_api_config()
        self.ayla_api = self.api_conf.get("AYLA")
        self._access_token: str | None = None

    @property
    def access_token(self) -> str:
        """Return a valid access token, refreshing it on demand."""
        if not self._access_token:
            self.refresh_access_token()
        return self._access_token or ""

    def get_refresh_token(self) -> str | None:
        """Read the refresh token from disk."""
        if os.path.exists(self.token_path):
            with open(self.token_path, "r", encoding="utf-8") as f:
                data = f.read()
                if data:
                    token_data = json.loads(data)
                    return token_data.get("refresh_token")
        return None

    def set_refresh_token(self, refresh_token: str) -> None:
        """Persist a refresh token without clobbering unrelated metadata."""
        os.makedirs(os.path.dirname(os.path.abspath(self.token_path)), exist_ok=True)
        token_data: dict[str, Any] = {}
        if os.path.exists(self.token_path):
            with open(self.token_path, "r", encoding="utf-8") as f:
                data = f.read()
                token_data = json.loads(data) if data else {}
        with open(self.token_path, "w", encoding="utf-8") as f:
            token_data["refresh_token"] = refresh_token
            f.write(json.dumps(token_data, indent=2))

    def refresh_access_token(self) -> str:
        """Exchange the stored refresh token for a new access token."""
        refresh_token = self.get_refresh_token()
        if not refresh_token:
            self.set_refresh_token("")
            raise ValueError(
                f"No refresh token found. Open {self.token_path} and add a valid refresh token."
            )

        response = requests.post(
            url=f"{self.ayla_api.get('OAUTH_URL')}/users/refresh_token.json",
            headers={
                "User-Agent": TOKEN_USER_AGENT,
                "Content-Type": "application/json",
            },
            json={"user": {"refresh_token": refresh_token}},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise ValueError(
                f"Failed to get access token: {response.status_code} {response.text}"
            )

        data = response.json()
        self._access_token = data["access_token"]
        self.set_refresh_token(data["refresh_token"])
        return self._access_token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        """Make an authenticated Ayla API request with one refresh-on-401 retry."""
        effective_timeout = timeout or self.timeout
        request_headers = {
            "User-Agent": API_USER_AGENT,
            "Authorization": f"auth_token {self.access_token}",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        response = requests.request(
            method=method,
            url=f"{self.ayla_api.get('API_URL')}{path}",
            headers=request_headers,
            params=params,
            json=json_body,
            timeout=effective_timeout,
        )
        if response.status_code == 401:
            self.refresh_access_token()
            request_headers["Authorization"] = f"auth_token {self.access_token}"
            response = requests.request(
                method=method,
                url=f"{self.ayla_api.get('API_URL')}{path}",
                headers=request_headers,
                params=params,
                json=json_body,
                timeout=effective_timeout,
            )

        response.raise_for_status()
        return response
