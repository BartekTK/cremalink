from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import SettingsConfigDict, BaseSettings


class ServerSettings(BaseSettings):
    server_ip: str = Field("127.0.0.1", validation_alias="SERVER_IP")
    server_port: int = Field(10280, validation_alias="SERVER_PORT")

    nudger_poll_interval: float = Field(1.0, validation_alias="NUDGER_POLL_INTERVAL")
    monitor_poll_interval: float = Field(5.0, validation_alias="MONITOR_POLL_INTERVAL")
    rekey_interval_seconds: float = Field(60.0, validation_alias="REKEY_INTERVAL_SECONDS")

    queue_max_size: int = Field(200, validation_alias="QUEUE_MAX_SIZE")
    log_ring_size: int = Field(200, validation_alias="LOG_RING_SIZE")

    device_register_verify: bool = Field(False, validation_alias="DEVICE_REGISTER_VERIFY")
    device_register_ca_path: Optional[str] = Field(None, validation_alias="DEVICE_REGISTER_CA_PATH")
    device_register_timeout: float = Field(10.0, validation_alias="DEVICE_REGISTER_TIMEOUT")
    enable_device_register: bool = Field(True, validation_alias="ENABLE_DEVICE_REGISTER")

    enable_nudger_job: bool = Field(True, validation_alias="ENABLE_NUDGER_JOB")
    enable_monitor_job: bool = Field(True, validation_alias="ENABLE_MONITOR_JOB")
    enable_rekey_job: bool = Field(True, validation_alias="ENABLE_REKEY_JOB")

    # Testing / determinism hooks
    fixed_random_2: Optional[str] = Field(None, validation_alias="FIXED_RANDOM_2")
    fixed_time_2: Optional[str] = Field(None, validation_alias="FIXED_TIME_2")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True, extra="ignore")


@lru_cache
def get_settings() -> ServerSettings:
    return ServerSettings()
