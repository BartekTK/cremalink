"""
This module provides classes for handling and decoding device properties.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from cremalink.core.binary import crc16_ccitt
from cremalink.parsing.recipes import RecipeSnapshot, decode_recipe_b64, decode_recipe_container
from cremalink.domain.beverages import DRINK_NAMES

# Maintenance property prefixes → human-readable metric names.
_MAINTENANCE_MAP: dict[str, str] = {
    "d510": "grounds_container",
    "d512": "descale_progress",
    "d513": "water_filter",
    "d550": "water_since_descale",
    "d551": "grounds_count",
    "d552": "total_descale_cycles",
    "d553": "total_water_dispensed",
    "d554": "total_filter_replacements",
    "d555": "water_since_filter",
    "d556": "water_hardness_setting",
}

# JSON counter property names → list of (property_name, key_prefix_to_strip).
_JSON_COUNTER_PROPS: list[str] = [
    "d702_tot_bev_other",
    "d733_tot_bev_counters",
    "d734_tot_bev_usage",
    "d735_iced_bev",
    "d736_mug_bev",
    "d737_mug_iced_bev",
    "d738_cold_brew_bev",
    "d739_taste_bev",
    "d740_water_qty_bev",
]

# Machine settings: d-number prefix → setting name.
_SETTINGS_PREFIXES: dict[str, str] = {
    "d281": "temperature",
    "d282": "auto_off",
    "d283": "water_hardness",
}


@dataclass
class PropertiesSnapshot:
    """
    A container for a snapshot of device properties at a specific time.

    This class holds the raw property data as received from the device,
    the timestamp of when it was received, and a dictionary for any parsed
    or processed values. It provides a helper method to easily access
    property values from the potentially nested raw data structure.

    Attributes:
        raw: The raw dictionary of properties from the device.
        received_at: The timestamp when the snapshot was taken.
        parsed: A dictionary to hold processed or parsed property values.
    """
    raw: dict[str, Any]
    received_at: Optional[datetime]
    parsed: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        """
        Safely retrieves a property by its name from the raw data.

        The properties data can come in different formats. This method checks
        for the property name as a direct key and also searches within the
        nested 'property' objects that are common in the API response.

        Args:
            name: The name of the property to retrieve.

        Returns:
            The property dictionary if found, otherwise None.
        """
        # First, check if the name is a top-level key in the raw dictionary.
        if name in self.raw:
            return self.raw[name]

        # If not, iterate through the values to find a nested property object.
        # This handles the common format: `{'some_id': {'property': {'name': name, ...}}}`
        for entry in self.raw.values():
            if isinstance(entry, dict) and entry.get("property", {}).get("name") == name:
                return entry
        return None

    def get_recipes(self, profile: Optional[int] = None) -> list[RecipeSnapshot]:
        """
        Extract and decode all recipe properties from the snapshot.

        Recipes are detected by name pattern (``d\\d+_rec_``) and value format.
        JSON container values (default recipes) are also decoded.

        Args:
            profile: If provided, filter to only this profile number (1-4).

        Returns:
            A list of decoded ``RecipeSnapshot`` objects.
        """
        recipes: list[RecipeSnapshot] = []
        recipe_pattern = re.compile(r"d\d+_rec_")

        for entry in self.raw.values():
            if not isinstance(entry, dict):
                continue
            prop = entry.get("property", {})
            name = prop.get("name", "")
            value = prop.get("value")
            if not value or not isinstance(value, str):
                continue
            if not recipe_pattern.search(name):
                continue

            if value.startswith("{"):
                # JSON container with default recipes.
                for snapshot in decode_recipe_container(value):
                    if profile is None or snapshot.profile == profile:
                        recipes.append(snapshot)
            else:
                # Individual base64-encoded recipe.
                snapshot = decode_recipe_b64(value)
                if snapshot is not None:
                    if profile is None or snapshot.profile == profile:
                        recipes.append(snapshot)

        return recipes

    def get_counters(self) -> dict[str, int]:
        """
        Extract beverage usage counters from properties whose names contain
        ``_id{N}_`` (e.g. ``d705_tot_id1_espr``).

        Returns:
            A dict mapping beverage names (or ``"unknown_0xNN"``) to their count.
        """
        counters: dict[str, int] = {}
        # Match property names like d705_tot_id1_espr, d709_id6_americano, etc.
        id_pattern = re.compile(r"d7\d{2}.*_id(\d+)")

        for entry in self.raw.values():
            if not isinstance(entry, dict):
                continue
            prop = entry.get("property", {})
            name = prop.get("name", "")
            value = prop.get("value")
            if value is None:
                continue

            m = id_pattern.match(name)
            if not m:
                continue

            try:
                count = int(value)
            except (ValueError, TypeError):
                continue

            bev_id = int(m.group(1))
            if bev_id in DRINK_NAMES:
                counters[DRINK_NAMES[bev_id]] = count
            else:
                counters[f"unknown_0x{bev_id:02x}"] = count

        return counters

    def get_profile_names(self) -> dict[int, str]:
        """Extract user profile names from d051/d052 (0xA4F0 frames).

        These properties contain D0 binary frames with UTF-16BE encoded
        profile names.  d051 holds profiles 1-3, d052 holds profile 4.

        Returns:
            A dict mapping profile number (1-4) to the profile name.
        """
        names: dict[int, str] = {}
        name_block_size = 22  # 11 UTF-16 characters = 22 bytes

        for prefix in ("d051", "d052"):
            b64 = self._get_prop_value(prefix)
            if not b64:
                continue

            result = self._decode_d0_frame(b64)
            if result is None:
                continue

            opcode, payload = result
            if opcode != 0xA4F0 or len(payload) < 4:
                continue

            first_profile = payload[0]
            last_profile = payload[1]
            pos = 2

            for profile_num in range(first_profile, last_profile + 1):
                # After the first name block, skip [0x0B, profile_num] separator.
                if profile_num > first_profile and pos < len(payload) and payload[pos] == 0x0B:
                    pos += 2

                end = min(pos + name_block_size, len(payload))
                name_bytes = payload[pos:end]
                pos = end

                if len(name_bytes) < 2:
                    continue
                try:
                    text = name_bytes.decode("utf-16-be", errors="replace")
                except Exception:
                    continue
                name = text.split("\x00")[0].strip().rstrip("\ufffd\uffff")
                if name:
                    names[profile_num] = name

        return names

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _get_prop_value(self, prefix: str) -> Optional[str]:
        """Find first property whose name starts with *prefix* and return its string value."""
        for entry in self.raw.values():
            if not isinstance(entry, dict):
                continue
            prop = entry.get("property", {})
            name = prop.get("name", "")
            if name.startswith(prefix):
                value = prop.get("value")
                if value is not None and isinstance(value, str):
                    return value
        return None

    def _get_prop_any_value(self, prefix: str) -> Any:
        """Find first property whose name starts with *prefix* and return its raw value."""
        for entry in self.raw.values():
            if not isinstance(entry, dict):
                continue
            prop = entry.get("property", {})
            name = prop.get("name", "")
            if name.startswith(prefix):
                value = prop.get("value")
                if value is not None:
                    return value
        return None

    def _decode_d0_frame(self, b64_str: str) -> Optional[tuple[int, bytes]]:
        """Decode a D0-marker binary frame from a base64 string.

        Returns:
            A tuple ``(opcode, payload)`` where *payload* is the bytes after
            the opcode and before the CRC, or ``None`` if decoding fails.
        """
        try:
            raw = base64.b64decode(b64_str)
        except Exception:
            return None
        if len(raw) < 6 or raw[0] != 0xD0:
            return None
        length = raw[1]
        frame_end = min(length + 1, len(raw))
        opcode = (raw[2] << 8) | raw[3]
        payload = raw[4:frame_end - 2]
        return (opcode, payload)

    # ------------------------------------------------------------------
    # Additional property extractors
    # ------------------------------------------------------------------

    def get_aggregate_counters(self) -> dict[str, int]:
        """Extract aggregate usage counters (d7xx without per-beverage ``_id{N}_``).

        Returns:
            A dict mapping cleaned counter labels to their integer values.
        """
        counters: dict[str, int] = {}
        id_pattern = re.compile(r"_id\d+")
        d7_pattern = re.compile(r"d7\d{2}_(.*)")

        for entry in self.raw.values():
            if not isinstance(entry, dict):
                continue
            prop = entry.get("property", {})
            name = prop.get("name", "")
            value = prop.get("value")
            if value is None:
                continue

            m = d7_pattern.match(name)
            if not m:
                continue
            if id_pattern.search(name):
                continue

            try:
                count = int(value)
            except (ValueError, TypeError):
                continue

            label = m.group(1)
            if label.startswith("tot_"):
                label = label[4:]
            counters[label] = count

        return counters

    def get_maintenance(self) -> dict[str, int]:
        """Extract maintenance metrics from known properties (d510-d556).

        Property values may be integers or string-encoded integers depending
        on the cloud transport.

        Returns:
            A dict mapping metric names to integer values.
        """
        result: dict[str, int] = {}
        for prefix, metric_name in _MAINTENANCE_MAP.items():
            value = self._get_prop_any_value(prefix)
            if value is not None:
                try:
                    result[metric_name] = int(value)
                except (ValueError, TypeError):
                    pass
        return result

    def get_favorites(self) -> dict[int, list[str]]:
        """Extract favorite beverages per profile from d265-d268.

        Decodes 0xACF0 binary frames containing ordered lists of
        favourite beverage IDs per profile.

        Returns:
            A dict mapping profile number (1-4) to a list of beverage names.
        """
        favorites: dict[int, list[str]] = {}
        for i in range(1, 5):
            prefix = f"d{264 + i}"
            b64 = self._get_prop_value(prefix)
            if not b64:
                continue

            result = self._decode_d0_frame(b64)
            if result is None:
                continue

            opcode, payload = result
            if opcode != 0xACF0 or len(payload) < 1:
                continue

            profile = payload[0]
            bev_ids = [b for b in payload[1:] if b != 0x00]
            bev_names = [
                DRINK_NAMES.get(bid, f"unknown_0x{bid:02x}") for bid in bev_ids
            ]
            if bev_names:
                favorites[profile] = bev_names

        return favorites

    def get_recipe_priority(self) -> dict[int, list[str]]:
        """Extract recipe display priority per profile from d261-d264.

        Decodes 0xA8F0 binary frames containing ordered lists of beverage IDs
        representing the display order on the machine screen.

        Returns:
            A dict mapping profile number (1-4) to an ordered list of beverage names.
        """
        priorities: dict[int, list[str]] = {}
        for i in range(1, 5):
            prefix = f"d{260 + i}"
            b64 = self._get_prop_value(prefix)
            if not b64:
                continue

            result = self._decode_d0_frame(b64)
            if result is None:
                continue

            opcode, payload = result
            if opcode != 0xA8F0 or len(payload) < 1:
                continue

            profile = payload[0]
            bev_ids = [b for b in payload[1:] if b != 0x00]
            bev_names = [
                DRINK_NAMES.get(bid, f"unknown_0x{bid:02x}") for bid in bev_ids
            ]
            if bev_names:
                priorities[profile] = bev_names

        return priorities

    def get_machine_settings(self) -> dict[str, int]:
        """Extract machine settings from d281-d283 (0x950F frames).

        The payload format is ``[00, param_id, 00, 00, 00, value]``.

        Returns:
            A dict with keys ``'temperature'``, ``'auto_off'``, ``'water_hardness'``.
        """
        settings: dict[str, int] = {}
        for prefix, setting_name in _SETTINGS_PREFIXES.items():
            b64 = self._get_prop_value(prefix)
            if not b64:
                continue

            result = self._decode_d0_frame(b64)
            if result is None:
                continue

            opcode, payload = result
            if opcode != 0x950F:
                continue

            # Payload: [00, param_id, 00, 00, 00, value]
            if len(payload) >= 6:
                settings[setting_name] = payload[5]

        return settings

    def get_active_profile(self) -> Optional[int]:
        """Extract the active profile number from d286 (0x95F0 frame).

        Returns:
            The profile number (1-4) or ``None`` if not available.
        """
        b64 = self._get_prop_value("d286")
        if not b64:
            return None

        result = self._decode_d0_frame(b64)
        if result is None:
            return None

        opcode, payload = result
        if opcode != 0x95F0 or len(payload) < 1:
            return None

        return payload[0]

    def get_serial_number(self) -> Optional[str]:
        """Extract the machine serial number from d270 (0xA10F frame).

        The payload format is ``[00, marker_byte, ASCII_serial, 00]``.

        Returns:
            The serial number string or ``None`` if not available.
        """
        b64 = self._get_prop_value("d270")
        if not b64:
            return None

        result = self._decode_d0_frame(b64)
        if result is None:
            return None

        opcode, payload = result
        if opcode != 0xA10F or len(payload) < 3:
            return None

        # Skip first 2 bytes (00, marker), read ASCII until null or end.
        serial_bytes = payload[2:]
        end = serial_bytes.find(0)
        if end >= 0:
            serial_bytes = serial_bytes[:end]
        try:
            return serial_bytes.decode("ascii")
        except (UnicodeDecodeError, ValueError):
            return None

    def get_bean_system(self) -> dict[int, str]:
        """Extract bean system names from d250-d256 (0xBAF0 frames).

        Each property contains a bean slot number and one or more UTF-16LE
        encoded names.  Only the first (primary) name is returned.

        Returns:
            A dict mapping bean slot number (0-6) to the primary bean name.
        """
        beans: dict[int, str] = {}
        for i in range(7):
            prefix = f"d{250 + i}"
            b64 = self._get_prop_value(prefix)
            if not b64:
                continue

            result = self._decode_d0_frame(b64)
            if result is None:
                continue

            opcode, payload = result
            if opcode != 0xBAF0 or len(payload) < 3:
                continue

            slot = payload[0]
            # Skip slot byte + 1 padding byte, decode UTF-16LE.
            try:
                text = payload[2:].decode("utf-16-le", errors="replace")
            except Exception:
                continue

            # Take first null-terminated name.
            name = text.split("\x00")[0].strip()
            if name and name != "\ufffd":
                beans[slot] = name

        return beans

    def get_service_parameters(self) -> dict[str, Any]:
        """Extract service parameters from d580 and d581 (JSON values).

        Returns:
            A dict of all service parameter key-value pairs.
        """
        params: dict[str, Any] = {}
        for prefix in ("d580", "d581"):
            value_str = self._get_prop_value(prefix)
            if not value_str:
                continue
            try:
                parsed = json.loads(value_str)
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        try:
                            params[k] = int(v)
                        except (ValueError, TypeError):
                            params[k] = v
            except (json.JSONDecodeError, TypeError):
                continue
        return params

    def get_json_counters(self) -> dict[str, int]:
        """Extract counters from JSON-valued d7xx properties.

        These properties (d702, d733-d740) contain JSON objects whose values
        are string-encoded integers.

        Returns:
            A flattened dict mapping counter labels to integer values.
        """
        counters: dict[str, int] = {}
        for prop_name in _JSON_COUNTER_PROPS:
            for entry in self.raw.values():
                if not isinstance(entry, dict):
                    continue
                prop = entry.get("property", {})
                name = prop.get("name", "")
                if name != prop_name:
                    continue
                value = prop.get("value")
                if not value or not isinstance(value, str):
                    break
                try:
                    parsed = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    break
                if isinstance(parsed, dict):
                    for k, v in parsed.items():
                        try:
                            counters[k] = int(v)
                        except (ValueError, TypeError):
                            pass
                break
        return counters

    def get_software_version(self) -> Optional[str]:
        """Extract the firmware software version string.

        Returns:
            The software version string or ``None``.
        """
        for entry in self.raw.values():
            if not isinstance(entry, dict):
                continue
            prop = entry.get("property", {})
            if prop.get("name") == "software_version":
                value = prop.get("value")
                if value and isinstance(value, str):
                    return value
        return None
