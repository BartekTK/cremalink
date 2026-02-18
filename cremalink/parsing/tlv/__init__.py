"""
TLV (Tag-Length-Value) codec for De'Longhi ECAM binary parameter encoding.

This sub-package provides functions to parse and encode TLV-encoded parameters
used in recipe data and brew commands. Parameters are identified by a single
byte tag, with values being either one or two bytes depending on the tag.
"""
from cremalink.parsing.tlv.decode import (
    encode_tlv_params,
    named_params,
    parse_tlv_params,
    PARAM_NAMES,
    PARAM_ORDER,
    TWO_BYTE_PARAMS,
)

__all__ = [
    "encode_tlv_params",
    "named_params",
    "parse_tlv_params",
    "PARAM_NAMES",
    "PARAM_ORDER",
    "TWO_BYTE_PARAMS",
]
