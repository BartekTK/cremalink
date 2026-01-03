from __future__ import annotations

from typing import Any, Optional

from cremalink.core.binary import get_bit
from cremalink.parsing.monitor.frame import MonitorFrame
from cremalink.parsing.monitor.model import MonitorSnapshot
from cremalink.parsing.monitor.profile import MonitorProfile, PredicateDefinition


class MonitorView:
    def __init__(self, snapshot: MonitorSnapshot, profile: MonitorProfile | dict[str, Any] | None = None) -> None:
        self.snapshot = snapshot
        self.profile = profile if isinstance(profile, MonitorProfile) else MonitorProfile.from_dict(profile or {})
        self._frame: Optional[MonitorFrame] = snapshot.frame
        if self._frame is None and snapshot.raw_b64:
            try:
                self._frame = MonitorFrame.from_b64(snapshot.raw_b64)
            except Exception:
                self._frame = None

    # --- raw accessors ---
    @property
    def raw(self) -> bytes:
        return self.snapshot.raw

    @property
    def raw_b64(self) -> str:
        return self.snapshot.raw_b64

    @property
    def parsed(self) -> dict[str, Any]:
        return self.snapshot.parsed

    @property
    def received_at(self):
        return self.snapshot.received_at

    # --- standard fields ---
    @property
    def status_code(self) -> Optional[int]:
        return self._frame.status if self._frame else None

    @property
    def action_code(self) -> Optional[int]:
        return self._frame.action if self._frame else None

    @property
    def progress_percent(self) -> Optional[int]:
        return self._frame.progress if self._frame else None

    @property
    def accessory_code(self) -> Optional[int]:
        return self._frame.accessory if self._frame else None

    # --- enum mapping ---
    def _enum_lookup(self, enum_name: str, code: Optional[int]) -> Optional[str]:
        if code is None:
            return None
        mapping = self.profile.enums.get(enum_name, {})
        return mapping.get(int(code), str(code))

    @property
    def status_name(self) -> Optional[str]:
        return self._enum_lookup("status", self.status_code)

    @property
    def action_name(self) -> Optional[str]:
        return self._enum_lookup("action", self.action_code)

    @property
    def accessory_name(self) -> Optional[str]:
        return self._enum_lookup("accessory", self.accessory_code)

    # --- flag/predicate helpers ---
    def _resolve_flag(self, flag_name: str) -> Optional[bool]:
        if not self._frame:
            return None
        flag_def = self.profile.flags.get(flag_name)
        if not flag_def:
            return None
        data_bytes = self._frame.alarms if flag_def.source == "alarms" else self._frame.switches
        if flag_def.byte >= len(data_bytes):
            return None
        byte_val = data_bytes[flag_def.byte]
        value = get_bit(byte_val, flag_def.bit)
        return not value if flag_def.invert else value

    def _source_value(self, source: str) -> Any:
        if not self._frame:
            return None
        return {
            "alarms": self._frame.alarms,
            "switches": self._frame.switches,
            "status": self._frame.status,
            "action": self._frame.action,
            "progress": self._frame.progress,
            "accessory": self._frame.accessory,
        }.get(source)

    def _evaluate_predicate(self, definition: PredicateDefinition) -> Optional[bool]:
        try:
            if definition.uses_flag():
                flag_value = self._resolve_flag(definition.flag or "")
                if flag_value is None:
                    return None
                return flag_value if definition.kind == "flag_true" else not flag_value

            if definition.uses_bit_address():
                if not self._frame or not definition.source:
                    return None
                source_bytes = self._frame.alarms if definition.source == "alarms" else self._frame.switches
                if definition.byte is None or definition.byte >= len(source_bytes) or definition.bit is None:
                    return None
                bit_value = get_bit(source_bytes[definition.byte], definition.bit)
                return bit_value if definition.kind == "bit_set" else not bit_value

            source_val = self._source_value(definition.source) if definition.source else None
            if definition.kind == "equals":
                return source_val == definition.value
            if definition.kind == "not_equals":
                return source_val != definition.value
            if definition.kind == "in_set":
                return source_val in set(definition.values or [])
            if definition.kind == "not_in_set":
                return source_val not in set(definition.values or [])
        except Exception:
            return None
        return None

    # --- dynamic access ---
    @property
    def available_fields(self) -> list[str]:
        return self.profile.available_fields()

    @property
    def profile_summary(self) -> dict[str, Any]:
        return self.profile.summary()

    def __getattr__(self, item: str) -> Any:
        if item in self.profile.flags:
            return self._resolve_flag(item)
        if item in self.profile.predicates:
            return self._evaluate_predicate(self.profile.predicates[item])
        raise AttributeError(f"{self.__class__.__name__} has no attribute '{item}'")
