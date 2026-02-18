"""
Beverage catalog for De'Longhi ECAM coffee machines.

Provides a complete catalog of 57 beverage IDs with human-readable names,
display names, categories, and milk indicators. The catalog is used by the
command builder and device interface to resolve beverage references.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BeverageCategory(str, Enum):
    """Categories for grouping beverages."""
    BLACK_COFFEE = "black_coffee"
    MILK_COFFEE = "milk_coffee"
    HOT_OTHER = "hot_other"
    ICED = "iced"
    MY = "my"
    MY_ICED = "my_iced"
    CARAFE = "carafe"
    SPECIAL = "special"


@dataclass(frozen=True)
class BeverageInfo:
    """
    Metadata for a single beverage type.

    Attributes:
        id: The numeric beverage ID used in the protocol.
        name: Machine-readable snake_case name.
        display_name: Human-readable display name.
        category: The beverage category.
        has_milk: Whether the beverage includes a milk step.
    """
    id: int
    name: str
    display_name: str
    category: BeverageCategory
    has_milk: bool


# Complete mapping of beverage IDs to snake_case names.
DRINK_NAMES: dict[int, str] = {
    0x01: "espresso",
    0x02: "coffee",
    0x03: "long_coffee",
    0x04: "double_espresso",
    0x05: "doppio_plus",
    0x06: "americano",
    0x07: "cappuccino",
    0x08: "latte_macchiato",
    0x09: "caffe_latte",
    0x0A: "flat_white",
    0x0B: "espresso_macchiato",
    0x0C: "hot_milk",
    0x0D: "cappuccino_doppio_plus",
    0x0F: "cappuccino_mix",
    0x10: "hot_water",
    0x16: "tea",
    0x17: "coffee_pot",
    0x18: "cortado",
    0x1B: "brew_over_ice",
    0x32: "iced_americano",
    0x33: "iced_cappuccino",
    0x34: "iced_latte_macchiato",
    0x35: "iced_cappuccino_mix",
    0x36: "iced_flat_white",
    0x37: "iced_cold_milk",
    0x38: "iced_caffe_latte",
    0x39: "over_ice_espresso",
    0x50: "my_americano",
    0x51: "my_cappuccino",
    0x52: "my_latte_macchiato",
    0x53: "my_caffe_latte",
    0x54: "my_cappuccino_mix",
    0x55: "my_flat_white",
    0x56: "my_hot_milk",
    0x64: "my_iced_over_ice",
    0x65: "my_iced_americano",
    0x66: "my_iced_cappuccino",
    0x67: "my_iced_latte_macchiato",
    0x68: "my_iced_caffe_latte",
    0x69: "my_iced_cappuccino_mix",
    0x6A: "my_iced_flat_white",
    0x6B: "my_iced_cold_milk",
    0x78: "carafe_coffee",
    0x79: "carafe_coffee_espresso",
    0x7A: "carafe_coffee_pot",
    0x7B: "carafe_latte",
    0x7C: "carafe_cappuccino",
    0x8C: "carafe_mug",
    0x8D: "carafe_latte_mug",
    0x8E: "carafe_cappuccino_mug",
    0xC8: "barista_special",
    0xE6: "custom_1",
    0xE7: "custom_2",
    0xE8: "custom_3",
    0xE9: "custom_4",
    0xEA: "custom_5",
    0xEB: "custom_6",
}

# Human-readable display names.
DISPLAY_NAMES: dict[str, str] = {
    "espresso": "Espresso",
    "coffee": "Coffee",
    "long_coffee": "Long Coffee",
    "double_espresso": "Double Espresso",
    "doppio_plus": "Doppio+",
    "americano": "Americano",
    "cappuccino": "Cappuccino",
    "latte_macchiato": "Latte Macchiato",
    "caffe_latte": "Caffe Latte",
    "flat_white": "Flat White",
    "espresso_macchiato": "Espresso Macchiato",
    "hot_milk": "Hot Milk",
    "cappuccino_doppio_plus": "Cappuccino Doppio+",
    "cappuccino_mix": "Cappuccino Mix",
    "hot_water": "Hot Water",
    "tea": "Tea",
    "coffee_pot": "Coffee Pot",
    "cortado": "Cortado",
    "brew_over_ice": "Brew Over Ice",
    "iced_americano": "Iced Americano",
    "iced_cappuccino": "Iced Cappuccino",
    "iced_latte_macchiato": "Iced Latte Macchiato",
    "iced_cappuccino_mix": "Iced Cappuccino Mix",
    "iced_flat_white": "Iced Flat White",
    "iced_cold_milk": "Iced Cold Milk",
    "iced_caffe_latte": "Iced Caffe Latte",
    "over_ice_espresso": "Over Ice Espresso",
    "my_americano": "My Americano",
    "my_cappuccino": "My Cappuccino",
    "my_latte_macchiato": "My Latte Macchiato",
    "my_caffe_latte": "My Caffe Latte",
    "my_cappuccino_mix": "My Cappuccino Mix",
    "my_flat_white": "My Flat White",
    "my_hot_milk": "My Hot Milk",
    "my_iced_over_ice": "My Iced Over Ice",
    "my_iced_americano": "My Iced Americano",
    "my_iced_cappuccino": "My Iced Cappuccino",
    "my_iced_latte_macchiato": "My Iced Latte Macchiato",
    "my_iced_caffe_latte": "My Iced Caffe Latte",
    "my_iced_cappuccino_mix": "My Iced Cappuccino Mix",
    "my_iced_flat_white": "My Iced Flat White",
    "my_iced_cold_milk": "My Iced Cold Milk",
    "carafe_coffee": "Carafe Coffee",
    "carafe_coffee_espresso": "Carafe Coffee Espresso",
    "carafe_coffee_pot": "Carafe Coffee Pot",
    "carafe_latte": "Carafe Latte",
    "carafe_cappuccino": "Carafe Cappuccino",
    "carafe_mug": "Carafe Mug",
    "carafe_latte_mug": "Carafe Latte Mug",
    "carafe_cappuccino_mug": "Carafe Cappuccino Mug",
    "barista_special": "Barista Special",
    "custom_1": "Custom 1",
    "custom_2": "Custom 2",
    "custom_3": "Custom 3",
    "custom_4": "Custom 4",
    "custom_5": "Custom 5",
    "custom_6": "Custom 6",
}

# Category assignments for each beverage ID.
_CATEGORY_MAP: dict[int, BeverageCategory] = {}
_cat_ranges: list[tuple[list[int], BeverageCategory]] = [
    ([0x01, 0x02, 0x03, 0x04, 0x05, 0x06], BeverageCategory.BLACK_COFFEE),
    ([0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0D, 0x0F, 0x18], BeverageCategory.MILK_COFFEE),
    ([0x0C, 0x10, 0x16, 0x17], BeverageCategory.HOT_OTHER),
    ([0x1B, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39], BeverageCategory.ICED),
    ([0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56], BeverageCategory.MY),
    ([0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B], BeverageCategory.MY_ICED),
    ([0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x8C, 0x8D, 0x8E], BeverageCategory.CARAFE),
    ([0xC8, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB], BeverageCategory.SPECIAL),
]
for _ids, _cat in _cat_ranges:
    for _bid in _ids:
        _CATEGORY_MAP[_bid] = _cat

# IDs that involve a milk dispensing step.
_MILK_IDS: frozenset[int] = frozenset({
    0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0F, 0x18,
    0x33, 0x34, 0x35, 0x36, 0x37, 0x38,
    0x51, 0x52, 0x53, 0x54, 0x55, 0x56,
    0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B,
    0x7B, 0x7C, 0x8D, 0x8E,
})


def _build_catalog() -> dict[int, BeverageInfo]:
    """Build the full catalog of BeverageInfo objects."""
    catalog: dict[int, BeverageInfo] = {}
    for bev_id, name in DRINK_NAMES.items():
        display = DISPLAY_NAMES.get(name, name.replace("_", " ").title())
        cat = _CATEGORY_MAP.get(bev_id, BeverageCategory.SPECIAL)
        catalog[bev_id] = BeverageInfo(
            id=bev_id,
            name=name,
            display_name=display,
            category=cat,
            has_milk=bev_id in _MILK_IDS,
        )
    return catalog


class BeverageCatalog:
    """
    Read-only catalog of all known ECAM beverages.

    Provides lookup by numeric ID, snake_case name, and category filtering.
    """

    def __init__(self) -> None:
        self._by_id: dict[int, BeverageInfo] = _build_catalog()
        self._by_name: dict[str, BeverageInfo] = {
            info.name: info for info in self._by_id.values()
        }

    def get_by_id(self, bev_id: int) -> Optional[BeverageInfo]:
        """
        Look up a beverage by its numeric protocol ID.

        Args:
            bev_id: The integer beverage ID.

        Returns:
            The ``BeverageInfo`` if found, otherwise ``None``.
        """
        return self._by_id.get(bev_id)

    def get_by_name(self, name: str) -> Optional[BeverageInfo]:
        """
        Look up a beverage by its snake_case name.

        Args:
            name: The beverage name (e.g. ``"espresso"``).

        Returns:
            The ``BeverageInfo`` if found, otherwise ``None``.
        """
        return self._by_name.get(name.lower().strip())

    def list_category(self, category: BeverageCategory) -> list[BeverageInfo]:
        """
        Return all beverages in a given category.

        Args:
            category: The category to filter by.

        Returns:
            A list of matching ``BeverageInfo`` objects, sorted by ID.
        """
        return sorted(
            (b for b in self._by_id.values() if b.category == category),
            key=lambda b: b.id,
        )

    def all(self) -> list[BeverageInfo]:
        """Return all beverages sorted by ID."""
        return sorted(self._by_id.values(), key=lambda b: b.id)

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, item: int | str) -> bool:
        if isinstance(item, int):
            return item in self._by_id
        return item in self._by_name
