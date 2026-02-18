"""
This package contains all modules related to parsing and decoding data
received from the coffee machine.

Sub-packages handle specific data formats:

- ``monitor``: Binary monitor frame decoding and interpretation.
- ``properties``: Device property snapshots and value extraction.
- ``tlv``: TLV (Tag-Length-Value) parameter codec.
- ``recipes``: Cloud recipe property decoding.
- ``commands``: Brew and stop command frame construction.
"""
