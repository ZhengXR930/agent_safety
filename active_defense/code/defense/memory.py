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
    # None means the registration substrate did not publish requiredness.
    # An empty tuple means it explicitly declared that no argument is required.
    required_arguments: tuple[str, ...] | None = None
    # (argument, resolver grammars) for open prose positions.  The grammar
    # names substrate parsers; an empty grammar tuple means inert prose.
    interprets: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @classmethod
    def from_dict(cls, value):
        effect = bool(value.get("effect", False))
        arguments = value.get("arguments") or value.get("params")
        required = value.get("required_arguments")
        interpretations = value.get("interprets") or {}
        if isinstance(interpretations, dict):
            interpretations = tuple(
                (str(name), tuple(map(str, grammars or ())))
                for name, grammars in interpretations.items()
                if str(name) in set(map(str, arguments or ()))
            )
        else:
            interpretations = ()
        if not arguments:
            schema = value.get("inputSchema")
            schema = schema if isinstance(schema, dict) else {}
            properties = schema.get("properties")
            arguments = list(properties) if isinstance(properties, dict) else []
            if "required" in schema:
                required = schema.get("required") or []
        elif "required_arguments" not in value:
            required = None
        return cls(str(value.get("name", "")), str(value.get("description", "")),
                   tuple(map(str, arguments or [])),
                   effect, bool(value.get("observation", not effect)),
                   None if required is None else tuple(map(str, required)),
                   interpretations)

    @property
    def required(self) -> tuple[str, ...]:
        """Conservative compatibility when an old manifest lacks requiredness."""
        return self.arguments if self.required_arguments is None else self.required_arguments

    def grammars(self, argument: str):
        for name, grammars in self.interprets:
            if name == str(argument):
                return grammars
        return None


@dataclass
class EnvironmentPlan:
    id: str = ""
    sources: dict[str, SourceSurface] = field(default_factory=dict)
    capabilities: dict[str, CapabilitySurface] = field(default_factory=dict)

    def to_dict(self):
        return {"id": self.id,
                "sources": {key: vars(value) for key, value in self.sources.items()},
                "capabilities": {key: {**vars(value),
                                      "arguments": list(value.arguments),
                                      "interprets": {
                                          name: list(grammars)
                                          for name, grammars in value.interprets
                                      },
                                      "required_arguments": (
                                          None if value.required_arguments is None
                                          else list(value.required_arguments))}
                            for key, value in self.capabilities.items()}}

    @classmethod
    def from_dict(cls, value):
        return cls(str(value.get("id", "")),
                   {key: SourceSurface.from_dict(item) for key, item in (value.get("sources") or {}).items()},
                   {key: CapabilitySurface.from_dict(item) for key, item in
                    (value.get("capabilities") or {}).items()})
