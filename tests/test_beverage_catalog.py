"""Tests for the BeverageCatalog and BeverageInfo."""
from cremalink.domain.beverages import (
    BeverageCatalog,
    BeverageCategory,
    BeverageInfo,
    DRINK_NAMES,
    DISPLAY_NAMES,
)


def test_catalog_has_57_beverages():
    catalog = BeverageCatalog()
    assert len(catalog) == 57


def test_get_by_id_espresso():
    catalog = BeverageCatalog()
    info = catalog.get_by_id(0x01)
    assert info is not None
    assert info.name == "espresso"
    assert info.display_name == "Espresso"
    assert info.category == BeverageCategory.BLACK_COFFEE
    assert info.has_milk is False


def test_get_by_id_cappuccino():
    catalog = BeverageCatalog()
    info = catalog.get_by_id(0x07)
    assert info is not None
    assert info.name == "cappuccino"
    assert info.has_milk is True
    assert info.category == BeverageCategory.MILK_COFFEE


def test_get_by_id_unknown():
    catalog = BeverageCatalog()
    assert catalog.get_by_id(0xFF) is None


def test_get_by_name():
    catalog = BeverageCatalog()
    info = catalog.get_by_name("flat_white")
    assert info is not None
    assert info.id == 0x0A
    assert info.has_milk is True


def test_get_by_name_case_insensitive():
    catalog = BeverageCatalog()
    info = catalog.get_by_name("  Flat_White  ")
    # Should normalize to lowercase and strip
    assert info is not None
    assert info.name == "flat_white"


def test_get_by_name_unknown():
    catalog = BeverageCatalog()
    assert catalog.get_by_name("unicorn_latte") is None


def test_list_category_black_coffee():
    catalog = BeverageCatalog()
    black = catalog.list_category(BeverageCategory.BLACK_COFFEE)
    assert len(black) == 6
    names = [b.name for b in black]
    assert "espresso" in names
    assert "americano" in names
    assert "cappuccino" not in names


def test_list_category_iced():
    catalog = BeverageCatalog()
    iced = catalog.list_category(BeverageCategory.ICED)
    assert len(iced) == 9
    assert all("iced" in b.name or "over_ice" in b.name or "brew_over" in b.name for b in iced)


def test_list_category_special():
    catalog = BeverageCatalog()
    special = catalog.list_category(BeverageCategory.SPECIAL)
    names = [b.name for b in special]
    assert "barista_special" in names
    assert "custom_1" in names


def test_all_sorted_by_id():
    catalog = BeverageCatalog()
    all_bevs = catalog.all()
    assert len(all_bevs) == 57
    ids = [b.id for b in all_bevs]
    assert ids == sorted(ids)


def test_contains_by_id():
    catalog = BeverageCatalog()
    assert 0x01 in catalog
    assert 0xFF not in catalog


def test_contains_by_name():
    catalog = BeverageCatalog()
    assert "espresso" in catalog
    assert "unicorn" not in catalog


def test_every_drink_name_has_display():
    for name in DRINK_NAMES.values():
        assert name in DISPLAY_NAMES, f"Missing display name for '{name}'"


def test_beverage_info_is_frozen():
    catalog = BeverageCatalog()
    info = catalog.get_by_id(0x01)
    try:
        info.name = "changed"
        assert False, "Should not allow mutation"
    except AttributeError:
        pass


def test_hot_milk_has_milk():
    catalog = BeverageCatalog()
    info = catalog.get_by_id(0x0C)
    assert info.name == "hot_milk"
    assert info.has_milk is True
    assert info.category == BeverageCategory.HOT_OTHER


def test_hot_water_no_milk():
    catalog = BeverageCatalog()
    info = catalog.get_by_id(0x10)
    assert info.name == "hot_water"
    assert info.has_milk is False
