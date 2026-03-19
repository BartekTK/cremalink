from cremalink.transports.cloud.transport import CloudTransport


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class StubAylaSession:
    def __init__(self):
        self.calls = []

    def request(self, method, path, *, params=None, json_body=None, headers=None, timeout=None):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "params": params,
                "json_body": json_body,
            }
        )
        if path == "/dsns/dsn-1.json":
            return DummyResponse(
                {
                    "device": {
                        "key": "device-key",
                        "model": "ECAM612",
                        "lan_enabled": True,
                        "type": "coffee_machine",
                        "connection_status": "Online",
                        "lan_ip": "1.2.3.4",
                    }
                }
            )
        if path == "/dsns/dsn-1/lan.json":
            return DummyResponse({"lanip": {"lanip_key": "lan-key"}})
        if path == "/dsns/dsn-1/properties.json":
            return DummyResponse(
                [{"property": {"name": params["names[]"], "value": "value"}}]
            )
        raise AssertionError(f"Unexpected request: {method} {path}")


def test_cloud_transport_uses_shared_session_for_requests():
    session = StubAylaSession()
    transport = CloudTransport(dsn="dsn-1", ayla_session=session)

    prop = transport.get_property("app_id")

    assert prop["name"] == "app_id"
    assert session.calls[0]["path"] == "/dsns/dsn-1.json"
    assert session.calls[1]["path"] == "/dsns/dsn-1/lan.json"
    assert session.calls[2]["path"] == "/dsns/dsn-1/properties.json"
    assert session.calls[2]["params"] == {"names[]": "app_id"}
