"""
Recipe decoding for De'Longhi ECAM cloud property values.

This sub-package decodes base64-encoded recipe data stored in the Ayla cloud
as device properties. Each recipe contains a beverage ID, optional profile
number, and TLV-encoded brewing parameters.
"""
from cremalink.parsing.recipes.decode import (
    RecipeSnapshot,
    decode_recipe_b64,
    decode_recipe_container,
)

__all__ = [
    "RecipeSnapshot",
    "decode_recipe_b64",
    "decode_recipe_container",
]
