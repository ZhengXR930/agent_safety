"""Persistent environment perception; no task or runtime trace is stored here."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceSurface:
    id: str
    description: str = ""
    plantable: bool = False

    @classmethod
    def from_dict(cls, value):
        return cls(str(value.get("id", "")), str(value.get("description", "")),
                   bool(value.get("plantable", False)))


RUNTIME_CONTEXT_SOURCE = SourceSurface(
    id="runtime-context",
    description="Operator-attested episode context",
    plantable=False,
)


@dataclass(frozen=True)
class CapabilitySurface:
    name: str
    description: str = ""
    arguments: tuple[str, ...] = ()
    effect: bool = False
    observation: bool = False

    @classmethod
    def from_dict(cls, value):
        effect = bool(value.get("effect", False))
        return cls(str(value.get("name", "")), str(value.get("description", "")),
                   tuple(map(str, value.get("arguments") or value.get("params") or [])),
                   effect, bool(value.get("observation", not effect)))


@dataclass
class EnvironmentPlan:
    id: str = ""
    sources: dict[str, SourceSurface] = field(default_factory=dict)
    capabilities: dict[str, CapabilitySurface] = field(default_factory=dict)

    def to_dict(self):
        return {"id": self.id,
                "sources": {key: vars(value) for key, value in self.sources.items()},
                "capabilities": {key: {**vars(value), "arguments": list(value.arguments)}
                            for key, value in self.capabilities.items()}}

    @classmethod
    def from_dict(cls, value):
        return cls(str(value.get("id", "")),
                   {key: SourceSurface.from_dict(item) for key, item in (value.get("sources") or {}).items()},
                   {key: CapabilitySurface.from_dict(item) for key, item in
                    (value.get("capabilities") or {}).items()})
