from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ConfigureRequest(BaseModel):
    dsn: str
    device_ip: str
    lan_key: str
    device_scheme: str = Field("https")
    monitor_property_name: str | None = None


class CommandRequest(BaseModel):
    command: str


class KeyExchange(BaseModel):
    random_1: str
    time_1: str | int


class KeyExchangeRequest(BaseModel):
    key_exchange: KeyExchange


class EncPayload(BaseModel):
    enc: str


class CommandPollResponse(BaseModel):
    enc: str
    sign: str
    seq: int


class MonitorResponse(BaseModel):
    monitor: Dict[str, Any] | Any | None = None
    monitor_b64: Optional[str] = None
    received_at: Optional[float] = None


class PropertiesResponse(BaseModel):
    properties: Dict[str, Any] = Field(default_factory=dict)
    received_at: Optional[float] = None
