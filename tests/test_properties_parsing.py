import datetime as dt

from cremalink.parsing.properties.decode import PropertiesSnapshot


def test_properties_snapshot_get():
    raw = {
        "prop1": {"property": {"name": "prop1", "value": "v1"}},
        "other": {"property": {"name": "other", "value": "v2"}},
    }
    snapshot = PropertiesSnapshot(raw=raw, received_at=dt.datetime.now(dt.UTC))
    assert snapshot.get("prop1")["property"]["value"] == "v1"
    assert snapshot.get("missing") is None
