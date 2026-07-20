"""Environment-only perception persisted before tasks arrive."""
from __future__ import annotations

import hashlib
import json

from .memory import CapabilitySurface, EnvironmentPlan, SourceSurface


class Surveyor:
    def __init__(self, client=None, model: str = ""):
        self.client, self.model = client, model

    def perceive(self, tool_schemas, source_carriers=()) -> EnvironmentPlan:
        """Normalize substrate-attested schemas; never predicts task flows or source relations."""
        raw_tools = list(tool_schemas or [])
        unknown = [raw for raw in raw_tools if "effect" not in raw]
        classified = self._classify(unknown) if unknown else {}
        capabilities = {}
        for raw in raw_tools:
            raw = dict(raw)
            if "effect" not in raw:
                raw["effect"] = classified.get(str(raw.get("name", "")), True)
            surface = CapabilitySurface.from_dict(raw)
            if surface.name:
                capabilities[surface.name] = surface
        sources = {}
        for raw in source_carriers or []:
            surface = SourceSurface.from_dict(raw)
            if surface.id:
                sources[surface.id] = surface
        body = json.dumps({"sources": sorted(sources),
                           "capabilities": {name: vars(value) for name, value in capabilities.items()}},
                          default=list, sort_keys=True,
                          separators=(",", ":"))
        return EnvironmentPlan("env-" + hashlib.sha256(body.encode()).hexdigest()[:12],
                               sources, capabilities)

    def perceive_skills(self, skill_files) -> EnvironmentPlan:
        """Read complete Skill manifests and extract only their public capability schema."""
        schemas, carriers = [], []
        for raw_path in sorted(map(str, skill_files)):
            from pathlib import Path
            path = Path(raw_path)
            manifest = path.read_text(encoding="utf-8", errors="ignore")
            name = path.parent.name
            schema = self._skill_schema(manifest)
            item = {"name": name, "description": manifest, **schema}
            schemas.append(item)
            if not schema["effect"]:
                carriers.append({"id": name, "carrier": str(path),
                                 "description": manifest, "plantable": True})
        return self.perceive(schemas, carriers)

    def _skill_schema(self, manifest: str) -> dict:
        if self.client is None:
            return {"effect": True, "arguments": [], "critical_arguments": []}
        from .session import ApiSession
        prompt = """Infer the public capability schema of this complete Skill manifest. This is
environment perception, not task planning. Return only JSON with exactly three fields: effect,
arguments, critical_arguments. effect is true only when invoking the Skill itself proposes or performs
a mutation, send, delete, scheduling, permission, authorization, install, or other externally consumed
commitment; it is false when the invocation only returns information, advice, or analysis. arguments are only public fields
stated by the manifest that bind the external commitment: invocation inputs for ordinary effects, or
emitted control fields for decision/authorization effects. Use [] when the manifest states neither.
Include every field explicitly declared in a public invocation signature or control output format,
including accompanying explanation/rationale fields; critical_arguments are only the fields needed to
identify what commitment is proposed. Do not infer a task flow or runtime values.

MANIFEST:
""" + manifest
        raw = ApiSession(self.client, self.model).ask_json(prompt)
        arguments = [str(value) for value in raw.get("arguments", [])]
        critical = [str(value) for value in raw.get("critical_arguments", [])
                    if str(value) in arguments]
        return {"effect": raw.get("effect") if isinstance(raw.get("effect"), bool) else True,
                "arguments": arguments, "critical_arguments": critical}

    def _classify(self, schemas) -> dict[str, bool]:
        if self.client is None:
            return {}
        from .session import ApiSession
        prompt = ("For every tool schema, decide one substrate fact: whether invoking the tool itself "
                  "creates a security-relevant effect. Return true for mutation, send, invite, delete, "
                  "publish, scheduling, authorization, or access/transmission to a caller-selected external "
                  "target. Return false when the call only observes task-platform state and merely returns "
                  "data. Do not classify the returned data or predict a task. Return only a JSON mapping "
                  "from every tool name to a boolean. Schemas: " +
                  json.dumps(schemas, ensure_ascii=False))
        result = ApiSession(self.client, self.model).ask_json(prompt)
        return {str(name): value if isinstance(value, bool) else True
                for name, value in result.items()}
