"""
This module provides classes for handling and decoding device properties.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from cremalink.parsing.recipes import RecipeSnapshot, decode_recipe_b64, decode_recipe_container
from cremalink.domain.beverages import DRINK_NAMES


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
        Extract beverage usage counters from properties in the d705-d738 range.

        Returns:
            A dict mapping beverage names (or ``"unknown_0xNN"``) to their count.
        """
        counters: dict[str, int] = {}
        counter_pattern = re.compile(r"d7\d{2}")

        for entry in self.raw.values():
            if not isinstance(entry, dict):
                continue
            prop = entry.get("property", {})
            name = prop.get("name", "")
            value = prop.get("value")
            if not counter_pattern.match(name) or value is None:
                continue

            try:
                count = int(value)
            except (ValueError, TypeError):
                continue

            # Counter properties encode the bev_id in the property name.
            # Extract it from the last two digits of the name.
            try:
                bev_id = int(name[1:], 10) - 705
                if bev_id in DRINK_NAMES:
                    counters[DRINK_NAMES[bev_id]] = count
                else:
                    counters[f"unknown_0x{bev_id:02x}"] = count
            except ValueError:
                pass

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
