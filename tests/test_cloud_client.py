import json
from unittest.mock import MagicMock, patch

from cremalink.clients.ayla import AylaSession
from cremalink.clients.cloud import Client


def test_set_refresh_token_preserves_other_keys(tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text(
        json.dumps({"refresh_token": "old-token", "dsn": "dsn-1"}),
        encoding="utf-8",
    )

    client = Client.__new__(Client)
    client.token_path = str(token_file)

    client._Client__set_refresh_token("new-token")

    data = json.loads(token_file.read_text(encoding="utf-8"))
    assert data["refresh_token"] == "new-token"
    assert data["dsn"] == "dsn-1"


def test_ayla_session_refreshes_and_retries_on_401(tmp_path):
    token_file = tmp_path / "token.json"
    token_file.write_text(
        json.dumps({"refresh_token": "old-refresh", "dsn": "dsn-1"}),
        encoding="utf-8",
    )

    session = AylaSession(str(token_file))
    session._access_token = "expired-token"

    refresh_response = MagicMock(status_code=200, text="")
    refresh_response.json.return_value = {
        "access_token": "fresh-token",
        "refresh_token": "new-refresh",
    }

    unauthorized = MagicMock(status_code=401, text="unauthorized")
    ok = MagicMock(status_code=200, text="")
    ok.raise_for_status.return_value = None

    with patch(
        "cremalink.clients.ayla.requests.post",
        return_value=refresh_response,
    ) as mock_post, patch(
        "cremalink.clients.ayla.requests.request",
        side_effect=[unauthorized, ok],
    ) as mock_request:
        response = session.request("GET", "/devices.json")

    assert response is ok
    assert mock_post.call_count == 1
    assert mock_request.call_count == 2
    assert mock_request.call_args_list[0].kwargs["headers"]["Authorization"] == "auth_token expired-token"
    assert mock_request.call_args_list[1].kwargs["headers"]["Authorization"] == "auth_token fresh-token"

    data = json.loads(token_file.read_text(encoding="utf-8"))
    assert data["refresh_token"] == "new-refresh"


def test_get_device_reuses_client_session():
    client = Client.__new__(Client)
    client.token_path = "token.json"
    client.ayla_session = object()
    client.devices = [{"device": {"dsn": "dsn-1"}}]

    with patch("cremalink.domain.create_cloud_device", return_value="device") as mock_create:
        device = client.get_device("dsn-1", device_map_path="map.json")

    assert device == "device"
    mock_create.assert_called_once_with(
        "dsn-1",
        device_map_path="map.json",
        ayla_session=client.ayla_session,
    )
