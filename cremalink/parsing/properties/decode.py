"""
This module provides classes for handling and decoding device properties.
"""
from __future__ import annotations

import base64
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
    "d513": "water_filter",
    "d550": "water_since_descale",
    "d551": "grounds_count",
    "d553": "total_water_dispensed",
    "d556": "water_hardness_setting",
}

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
        """
        Extract user profile names from properties d051-d054.

        Returns:
            A dict mapping profile number (1-4) to the profile name.
        """
        names: dict[int, str] = {}
        for i in range(1, 5):
            prop_name = f"d05{i}"
            entry = self.get(prop_name)
            if entry and isinstance(entry, dict):
                value = entry.get("property", {}).get("value")
                if value and isinstance(value, str):
                    names[i] = value
        return names

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _get_prop_value(self, prefix: str) -> Optional[str]:
        """Find first property whose name starts with *prefix* and return its value."""
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

        Returns:
            A dict mapping metric names to integer values.
        """
        result: dict[str, int] = {}
        for prefix, metric_name in _MAINTENANCE_MAP.items():
            value_str = self._get_prop_value(prefix)
            if value_str is not None:
                try:
                    result[metric_name] = int(value_str)
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
