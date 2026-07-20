"""Persistent environment perception; no task or runtime trace is stored here."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceSurface:
    id: str
    carrier: str
    description: str = ""
    plantable: bool = False

    @classmethod
    def from_dict(cls, value): return cls(**value)


@dataclass(frozen=True)
class CapabilitySurface:
    name: str
    description: str = ""
    arguments: tuple[str, ...] = ()
    critical_arguments: tuple[str, ...] = ()
    effect: bool = False

    @classmethod
    def from_dict(cls, value):
        return cls(str(value.get("name", "")), str(value.get("description", "")),
                   tuple(map(str, value.get("arguments") or value.get("params") or [])),
                   tuple(map(str, value.get("critical_arguments") or [])),
                   bool(value.get("effect", False)))


@dataclass
class EnvironmentPlan:
    id: str = ""
    sources: dict[str, SourceSurface] = field(default_factory=dict)
    capabilities: dict[str, CapabilitySurface] = field(default_factory=dict)

    def to_dict(self):
        return {"id": self.id,
                "sources": {key: vars(value) for key, value in self.sources.items()},
                "capabilities": {key: {**vars(value), "arguments": list(value.arguments),
                                    "critical_arguments": list(value.critical_arguments)}
                            for key, value in self.capabilities.items()}}

    @classmethod
    def from_dict(cls, value):
        return cls(str(value.get("id", "")),
                   {key: SourceSurface.from_dict(item) for key, item in (value.get("sources") or {}).items()},
                   {key: CapabilitySurface.from_dict(item) for key, item in
                    (value.get("capabilities") or {}).items()})
