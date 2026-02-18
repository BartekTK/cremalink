"""
This package defines the core domain models for the cremalink library,
representing the main entities like the coffee machine itself.

It exposes the primary `Device` class, factory functions for creating
device instances, and the beverage catalog.
"""
from cremalink.domain.beverages import BeverageCatalog
from cremalink.domain.device import Device
from cremalink.domain.factory import create_cloud_device, create_local_device

__all__ = ["BeverageCatalog", "Device", "create_cloud_device", "create_local_device"]
