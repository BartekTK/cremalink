"""
Command frame builder for De'Longhi ECAM coffee machines.

This sub-package constructs binary command frames for brew and stop operations,
encoding TLV parameters and appending CRC-16 checksums.
"""
from cremalink.parsing.commands.builder import (
    build_brew_command,
    build_stop_command,
    BREW_OPCODE_HI,
    BREW_OPCODE_LO,
    COMMAND_MARKER,
    TRIGGER_START,
    TRIGGER_STOP,
)

__all__ = [
    "build_brew_command",
    "build_stop_command",
    "BREW_OPCODE_HI",
    "BREW_OPCODE_LO",
    "COMMAND_MARKER",
    "TRIGGER_START",
    "TRIGGER_STOP",
]
