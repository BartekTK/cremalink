from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

VALID_SOURCES = {"alarms", "switches", "status", "action", "progress", "accessory"}


@dataclass
class FlagDefinition:
    source: str
    byte: int
    bit: int
    invert: bool = False
    description: Optional[str] = None

    def validate(self) -> None:
        if self.source not in {"alarms", "switches"}:
            raise ValueError("flag source must be 'alarms' or 'switches'")
        if self.byte < 0:
            raise ValueError("byte must be non-negative")
        if self.bit < 0 or self.bit > 7:
            raise ValueError("bit must be between 0 and 7")


@dataclass
class PredicateDefinition:
    kind: str
    source: Optional[str] = None
    value: Any = None
    values: Iterable[Any] | None = None
    flag: str | None = None
    byte: int | None = None
    bit: int | None = None

    def validate(self) -> None:
        if self.kind not in {
            "equals",
            "not_equals",
            "in_set",
            "not_in_set",
            "flag_true",
            "flag_false",
            "bit_set",
            "bit_clear",
        }:
            raise ValueError(f"Unsupported predicate kind: {self.kind}")
        if self.source and self.source not in VALID_SOURCES:
            raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}")
        if self.bit is not None and (self.bit < 0 or self.bit > 7):
            raise ValueError("bit must be between 0 and 7")

    def uses_flag(self) -> bool:
        return self.kind in {"flag_true", "flag_false"}

    def uses_bit_address(self) -> bool:
        return self.kind in {"bit_set", "bit_clear"}


@dataclass
class MonitorProfile:
    flags: Dict[str, FlagDefinition] = field(default_factory=dict)
    enums: Dict[str, Dict[int, str]] = field(default_factory=dict)
    predicates: Dict[str, PredicateDefinition] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict | None) -> "MonitorProfile":
        if not data:
            return cls()
        flags = {}
        for name, flag_data in (data.get("flags") or {}).items():
            flag = FlagDefinition(
                source=flag_data.get("source"),
                byte=int(flag_data.get("byte", 0)),
                bit=int(flag_data.get("bit", 0)),
                invert=bool(flag_data.get("invert", False)),
                description=flag_data.get("description"),
            )
            flag.validate()
            flags[name] = flag

        predicates = {}
        for name, pred_data in (data.get("predicates") or {}).items():
            pred = PredicateDefinition(
                kind=pred_data.get("kind"),
                source=pred_data.get("source"),
                value=pred_data.get("value"),
                values=pred_data.get("values") or pred_data.get("set") or pred_data.get("in"),
                flag=pred_data.get("flag"),
                byte=pred_data.get("byte"),
                bit=pred_data.get("bit"),
            )
            pred.validate()
            predicates[name] = pred

        enums = {
            name: {int(k): v for k, v in (mapping or {}).items()}
            for name, mapping in (data.get("enums", {}) or {}).items()
        }

        return cls(flags=flags, enums=enums, predicates=predicates)

    def available_fields(self) -> list[str]:
        dynamic = list(self.flags.keys()) + list(self.predicates.keys())
        return sorted(set(dynamic))

    def summary(self) -> dict[str, Any]:
        return {
            "flags": list(self.flags.keys()),
            "enums": {name: list(mapping.keys()) for name, mapping in self.enums.items()},
            "predicates": list(self.predicates.keys()),
        }


__all__ = ["FlagDefinition", "PredicateDefinition", "MonitorProfile"]
