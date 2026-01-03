import logging
import threading
from collections import deque
from typing import Deque, Dict, List, Optional


class RingBufferHandler(logging.Handler):
    def __init__(self, max_entries: int = 200):
        super().__init__()
        self.max_entries = max_entries
        self._events: Deque[Dict] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        event = {
            "event": record.getMessage(),
            "level": record.levelname,
            "ts": record.created,
            "details": getattr(record, "details", {}),
        }
        with self._lock:
            self._events.append(event)

    def get_events(self) -> List[Dict]:
        with self._lock:
            return list(self._events)


def create_logger(name: str, ring_size: int) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = RingBufferHandler(max_entries=ring_size)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def redact(details: Optional[dict]) -> dict:
    if not details:
        return {}
    redacted_keys = {"lan_key", "app_crypto_key", "dev_crypto_key", "app_iv_seed", "dev_iv_seed", "enc", "sign"}
    cleaned = {}
    for key, value in details.items():
        if key in redacted_keys:
            cleaned[key] = "***"
        else:
            cleaned[key] = value
    return cleaned
