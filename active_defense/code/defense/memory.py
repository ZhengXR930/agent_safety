"""Persistent environment perception; no task or runtime trace is stored here."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from urllib.parse import urlsplit, urlunsplit


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
    # Operator/substrate-attested JSON Schema for the canonical tool return.
    # None means the boundary did not publish an output contract.
    output_schema: dict | None = None
    # Operator/substrate-attested schema per call argument.  This is retained
    # only for deterministic shape/format handling, never semantic authority.
    argument_schemas: tuple[tuple[str, dict], ...] = ()
    # True only when the operator attests that this observation is produced
    # by committing the same effectful call (rather than by a read boundary).
    effect_return: bool = False

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
        output_schema = (value.get("output_schema")
                         if "output_schema" in value else value.get("outputSchema"))
        argument_schemas = value.get("argument_schemas")
        if argument_schemas is None:
            input_schema = value.get("inputSchema")
            input_schema = input_schema if isinstance(input_schema, dict) else {}
            argument_schemas = input_schema.get("properties") or {}
        if not isinstance(argument_schemas, dict):
            raise TypeError(
                f"capability {value.get('name', '')!r} argument schemas must be an object")
        if output_schema is not None and not isinstance(output_schema, dict):
            raise TypeError(
                f"capability {value.get('name', '')!r} output schema must be an object")
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
                   interpretations,
                   None if output_schema is None else dict(output_schema),
                   tuple((str(name), dict(schema))
                         for name, schema in argument_schemas.items()
                         if str(name) in set(map(str, arguments or ())) and
                         isinstance(schema, dict)),
                   bool(value.get("effect_return", False)))

    @property
    def required(self) -> tuple[str, ...]:
        """Conservative compatibility when an old manifest lacks requiredness."""
        return self.arguments if self.required_arguments is None else self.required_arguments

    @property
    def committed_return(self) -> bool:
        """Whether a passed call has an operator-attested canonical return.

        A dual outbound/inbound capability with a published output schema is
        already an attestation that the effect call returns this observation.
        The legacy explicit bit remains sufficient for other substrates.
        """
        return bool(self.effect_return or (
            self.effect and self.observation and self.output_schema is not None))

    def grammars(self, argument: str):
        for name, grammars in self.interprets:
            if name == str(argument):
                return grammars
        return None

    def argument_schema(self, argument: str):
        for name, schema in self.argument_schemas:
            if name == str(argument):
                return schema
        return None


def _schema_format(schema):
    if not isinstance(schema, dict):
        return None
    direct = schema.get("format")
    if isinstance(direct, str):
        return direct
    formats = {item for branch in (schema.get("anyOf") or schema.get("oneOf") or ())
               if (item := _schema_format(branch)) is not None}
    return next(iter(formats)) if len(formats) == 1 else None


def _canonical_temporal(value, format_name):
    if not isinstance(value, str):
        return value
    text = value.strip()
    try:
        if format_name == "date":
            return date.fromisoformat(text).isoformat()
        if format_name != "date-time":
            return value
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc)
        return parsed.isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return value


def _url_origin(value):
    canonical = _canonical_url(value)
    if not isinstance(canonical, str):
        return None
    try:
        parsed = urlsplit(canonical)
    except ValueError:
        return None
    return (parsed.scheme, parsed.netloc) if parsed.scheme and parsed.netloc else None


def _canonical_url(value):
    if not isinstance(value, str) or not value.strip():
        return value
    text = value.strip()
    if "://" not in text:
        text = "https://" + text
    try:
        parsed = urlsplit(text)
        if not parsed.hostname:
            return value
        host = parsed.hostname.lower()
        port = parsed.port
    except ValueError:
        return value
    if port is not None and not (
            parsed.scheme.lower() == "https" and port == 443):
        host += ":" + str(port)
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), host, path,
                       parsed.query, parsed.fragment))


def schema_values_equal(schema, left, right) -> bool:
    """Compare only equivalences explicitly enabled by an argument schema."""
    if left == right:
        return True
    if (isinstance(schema, dict) and
            schema.get("x-canonicalization") == "url-default-https"):
        return _canonical_url(left) == _canonical_url(right)
    format_name = _schema_format(schema)
    if format_name not in {"date", "date-time"}:
        return False
    return _canonical_temporal(left, format_name) == _canonical_temporal(right, format_name)


def argument_values_equal(surface, argument: str, left, right) -> bool:
    schema = surface.argument_schema(argument) if surface is not None else None
    return schema_values_equal(schema, left, right)


def argument_value_within_scope(surface, argument: str, root, candidate) -> bool:
    """Check a capability-argument scope explicitly attested by its manifest."""
    schema = surface.argument_schema(argument) if surface is not None else None
    return bool(isinstance(schema, dict) and
                schema.get("x-authority-scope") == "same-origin" and
                _url_origin(root) is not None and
                _url_origin(root) == _url_origin(candidate))


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
                                          else list(value.required_arguments)),
                                      "output_schema": value.output_schema,
                                      "argument_schemas": {
                                          name: schema for name, schema
                                          in value.argument_schemas
                                      }}
                            for key, value in self.capabilities.items()}}

    @classmethod
    def from_dict(cls, value):
        return cls(str(value.get("id", "")),
                   {key: SourceSurface.from_dict(item) for key, item in (value.get("sources") or {}).items()},
                   {key: CapabilitySurface.from_dict(item) for key, item in
                    (value.get("capabilities") or {}).items()})
