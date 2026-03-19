from __future__ import annotations

import json
import os

from cremalink.clients.ayla import AylaSession
from cremalink.clients.auth import authenticate_gigya


class Client:
    """
    Client for interacting with the Ayla IoT cloud platform.
    Manages authentication (access and refresh tokens) and device discovery.
    """

    @classmethod
    def from_credentials(
        cls,
        email: str,
        password: str,
        token_path: str,
    ) -> "Client":
        """
        Create a Client by authenticating with email and password.

        Performs the full Gigya OIDC authentication flow to obtain tokens,
        saves the refresh token to ``token_path``, then delegates to the
        standard ``__init__`` for token-based initialization.

        Args:
            email: The De'Longhi account email address.
            password: The De'Longhi account password.
            token_path: Path to a ``.json`` file for storing the refresh token.

        Returns:
            An authenticated ``Client`` instance.
        """
        tokens = authenticate_gigya(email, password)
        # Save refresh token so subsequent Client() calls can use it.
        os.makedirs(os.path.dirname(os.path.abspath(token_path)), exist_ok=True)
        with open(token_path, "w") as f:
            json.dump({"refresh_token": tokens.refresh_token}, f, indent=2)
        return cls(token_path)

    def __init__(self, token_path: str):
        self.token_path = token_path
        self.ayla_session = AylaSession(token_path)
        # Fetch the list of devices associated with the account.
        self.devices = self.ayla_session.request("GET", "/devices.json").json()

    @property
    def access_token(self) -> str:
        """Return the current Ayla access token."""
        return self._get_ayla_session().access_token

    def _get_ayla_session(self) -> AylaSession:
        """Lazily create the shared Ayla session.

        Some tests instantiate ``Client`` with ``__new__`` to exercise token-file
        helpers without running the full networked initializer.
        """
        session = getattr(self, "ayla_session", None)
        if session is None:
            session = AylaSession(self.token_path)
            self.ayla_session = session
        return session

    def get_devices(self):
        """
        Retrieves a list of Device Serial Numbers (DSNs) for all registered devices.

        Returns:
            list[str]: A list of DSNs.
        """
        devices: list[str] = []
        for device in self.devices:
            devices.append(device["device"]["dsn"])
        return devices

    def get_device(self, dsn: str, device_map_path: str | None = None):
        """
        Retrieves a specific cloud device by its DSN.

        Args:
            dsn (str): The Device Serial Number of the desired device.
            device_map_path (str | None): Optional path to a device map file.

        Returns:
            CloudDevice | None: An instance of CloudDevice if found, otherwise None.
        """
        from cremalink.domain import create_cloud_device

        for device_dsn in self.get_devices():
            if device_dsn == dsn:
                return create_cloud_device(
                    device_dsn,
                    device_map_path=device_map_path,
                    ayla_session=self._get_ayla_session(),
                )
        return None

    def __get_access_token(self):
        """
        Retrieves a valid access token, refreshing it if necessary using the refresh token.
        """
        return self._get_ayla_session().refresh_access_token()

    def __get_refresh_token(self):
        """
        Reads the refresh token from the token file.

        Returns:
            str | None: The refresh token if found, otherwise None.
        """
        return self._get_ayla_session().get_refresh_token()

    def __set_refresh_token(self, refresh_token: str):
        """
        Writes the provided refresh token to the token file.

        Args:
            refresh_token (str): The new refresh token to store.
        """
        self._get_ayla_session().set_refresh_token(refresh_token)
