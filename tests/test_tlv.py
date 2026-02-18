"""Tests for TLV codec (parse, encode, round-trip, edge cases)."""
from cremalink.parsing.tlv import (
    encode_tlv_params,
    named_params,
    parse_tlv_params,
    PARAM_NAMES,
    TWO_BYTE_PARAMS,
)


def test_parse_single_one_byte_param():
    # taste (0x1b) = 4
    data = bytes([0x1B, 0x04])
    result = parse_tlv_params(data)
    assert result == {0x1B: 4}


def test_parse_single_two_byte_param():
    # coffee_ml (0x01) = 36 (0x0024)
    data = bytes([0x01, 0x00, 0x24])
    result = parse_tlv_params(data)
    assert result == {0x01: 0x0024}


def test_parse_mixed_params():
    # aroma=1, coffee_ml=100, taste=4, temperature=2
    data = bytes([0x19, 0x01, 0x01, 0x00, 0x64, 0x1B, 0x04, 0x02, 0x05])
    result = parse_tlv_params(data)
    assert result == {0x19: 1, 0x01: 100, 0x1B: 4, 0x02: 5}


def test_parse_empty():
    assert parse_tlv_params(b"") == {}


def test_parse_truncated_two_byte():
    # Tag 0x01 (2-byte) but only 1 byte follows -> should stop gracefully
    data = bytes([0x01, 0x00])
    result = parse_tlv_params(data)
    assert result == {}


def test_parse_truncated_one_byte():
    # Tag 0x1b (1-byte) with no value following
    data = bytes([0x1B])
    result = parse_tlv_params(data)
    assert result == {}


def test_encode_single_param():
    params = {0x1B: 4}
    result = encode_tlv_params(params)
    assert result == bytes([0x1B, 0x04])


def test_encode_two_byte_param():
    params = {0x01: 0x0024}
    result = encode_tlv_params(params)
    assert result == bytes([0x01, 0x00, 0x24])


def test_encode_canonical_order():
    # Even though we pass in arbitrary order, output follows PARAM_ORDER
    params = {0x02: 5, 0x01: 100, 0x19: 1, 0x1B: 4}
    result = encode_tlv_params(params)
    # Expected order from PARAM_ORDER: 0x19, 0x01, 0x1B, 0x02
    expected = bytes([0x19, 0x01, 0x01, 0x00, 0x64, 0x1B, 0x04, 0x02, 0x05])
    assert result == expected


def test_roundtrip():
    original = {0x01: 256, 0x09: 120, 0x0F: 250, 0x19: 2, 0x1B: 3, 0x02: 5}
    encoded = encode_tlv_params(original)
    decoded = parse_tlv_params(encoded)
    assert decoded == original


def test_roundtrip_all_two_byte():
    params = {0x01: 500, 0x09: 300, 0x0F: 150}
    encoded = encode_tlv_params(params)
    decoded = parse_tlv_params(encoded)
    assert decoded == params


def test_named_params_known():
    params = {0x01: 100, 0x1B: 4, 0x02: 5}
    result = named_params(params)
    assert result == {"coffee_ml": 100, "taste": 4, "temperature": 5}


def test_named_params_unknown_tag():
    params = {0x01: 100, 0x99: 7}
    result = named_params(params)
    assert result["coffee_ml"] == 100
    assert result["0x99"] == 7


def test_all_known_params_have_names():
    for tag in TWO_BYTE_PARAMS:
        assert tag in PARAM_NAMES, f"TWO_BYTE_PARAM 0x{tag:02x} missing from PARAM_NAMES"


def test_encode_unknown_tag_appended():
    # Unknown tag 0xFF should be appended after known tags
    params = {0xFF: 42, 0x19: 1}
    result = encode_tlv_params(params)
    # 0x19 first (in PARAM_ORDER), then 0xFF
    assert result == bytes([0x19, 0x01, 0xFF, 0x2A])
