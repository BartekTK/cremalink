from __future__ import annotations

from typing import Optional

from cremalink.domain.device import Device
from cremalink.transports.cloud.transport import CloudTransport
from cremalink.transports.local.transport import LocalTransport


def create_local_device(
    dsn: str,
    lan_key: str,
    device_ip: Optional[str],
    server_host: str,
    server_port: int = 10280,
    device_scheme: str = "http",
    auto_configure: bool = True,
    device_map_path: Optional[str] = None,
) -> Device:
    transport = LocalTransport(
        dsn=dsn,
        lan_key=lan_key,
        device_ip=device_ip,
        server_host=server_host,
        server_port=server_port,
        device_scheme=device_scheme,
        auto_configure=auto_configure,
    )
    return Device.from_map(
        transport=transport,
        device_map_path=device_map_path,
        dsn=dsn,
        ip=device_ip,
        lan_key=lan_key,
        scheme=device_scheme,
    )


def create_cloud_device(
    dsn: str,
    access_token: str,
    device_map_path: Optional[str] = None,
) -> Device:
    transport = CloudTransport(dsn=dsn, access_token=access_token, device_map_path=device_map_path)
    return Device.from_map(
        transport=transport,
        device_map_path=device_map_path,
        dsn=dsn,
        model=getattr(transport, "model", None),
        ip=getattr(transport, "ip", None),
        lan_key=getattr(transport, "lan_key", None),
        is_online=getattr(transport, "is_online", None),
    )
