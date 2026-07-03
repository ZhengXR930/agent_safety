"""Backend-adapter layer (backend_adapters.py — distinct from agent_runtime.py, the agent-CLI runtime).

ONE uniform path for every primitive:backend, so the Engine + Detector do not hard-code per-type
branches and MCP is not a separate benchmark-runner path.

Registry key = "<primitive>:<placement|backend>":
  plant:sweep | plant:exfil | plant:reference | plant:basis
  wrap:file_shim | wrap:mcp_mediator | wrap:audit_only | wrap:rpc_proxy | wrap:egress_proxy

Every adapter exposes the same verbs:
  enrich(unit, work, prior_benign, conventions) -> dict   (per-unit context: plant/ wrap slice)
  deploy(decoy, work)         -> DeployRecord   (inject a PLANT / place a WRAP recorder, or skip w/ reason)
  read_records(work, decoy)   -> list[CallRecord]  (WRAP recorders emit CallRecords; PLANT returns [])
  agent_config(decoys, work)  -> dict            (extra agent_runtime.run_turn kwargs, e.g. an MCP --mcp-config)

The Detector consumes only CallRecord (with its `entry` = the actual capability/tool crossed) — it does
not know which backend produced it.

COVERAGE (honest — the abstraction is in place, the backends are NOT all fully implemented):
  * plant:*        implemented (file/dir/json/text carriers).
  * wrap:file_shim implemented (record-first shims on skill/local-tool entries).
  * wrap:mcp_mediator being folded into the Engine — deploy/agent_config/read_records exist; needs the
    MCP tool schema seeded (Env.meta["mcp_tools"] / carrier_file json / unit.mcp_tools).
  * wrap:audit_only two-state fallback: records if entries exist (status 'audit_only'), else 'skipped'.
  * wrap:rpc_proxy / wrap:egress_proxy  DECLARED but UNIMPLEMENTED (no proxy runtime) — deploy is an
    honest skip; a real runtime (rpc/egress proxy process + agent env-injection) is future work.
NAMING (do not confuse):  Adapter (adapters.py) = benchmark/Env adapter · BackendAdapter (this file) =
defense deployment adapter · agent_runtime.py = runs the target agent.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import agent_runtime, helpers

_MEDIATOR = str((Path(__file__).resolve().parent / "mcp_mediator.py"))


@dataclass
class DeployRecord:
    """Auditable outcome of deploying one decoy.  Detection runs on ACTIVE decoys (status 'deployed' =
    hard recorder, or 'audit_only' = recorder with no hard verdict); 'skipped'/'failed' are excluded."""
    uid: str
    primitive: str
    status: str = "deployed"          # deployed | audit_only | skipped | failed
    artifact_paths: list = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return {"uid": self.uid, "primitive": self.primitive, "status": self.status,
                "reason": self.reason, "artifacts": list(self.artifact_paths)}


@dataclass
class CallRecord:
    """A single mediated capability call, normalized across backends (file shim / MCP / ...)."""
    uid: str
    backend: str
    entry: str = ""
    args: list = field(default_factory=list)      # positional argv (file_shim)
    kwargs: dict = field(default_factory=dict)     # named args (mcp)
    timestamp: str = ""

    def values(self) -> list:
        """All identity-bearing values in the call (positional + named), for the argv envelope."""
        return [str(a) for a in self.args] + [str(v) for v in self.kwargs.values()]


def key_for(decoy) -> str:
    return f"plant:{decoy.placement}" if decoy.primitive == "plant" else f"wrap:{decoy.wrap_backend}"


class BackendAdapter:
    """Default: no context, nothing deployed, no records, no agent config.  Concrete adapters override."""
    key = "base"

    def enrich(self, unit, work: Path, prior_benign=None, conventions: str = "") -> dict:
        return {}

    def deploy(self, decoy, work: Path) -> DeployRecord:
        return DeployRecord(decoy.uid, decoy.primitive, "skipped", reason=f"{self.key}: no adapter")

    def read_records(self, work: Path, decoy) -> list:
        return []

    def agent_config(self, decoys: list, work: Path) -> dict:
        return {}


# ---------------------------- shared context helpers (code-only enrich) ----------------------------
def _load(cf: Path, default):
    try:
        return json.loads(cf.read_text(encoding="utf-8")) if cf and cf.exists() else default
    except (json.JSONDecodeError, OSError, UnicodeDecodeError, ValueError):
        return default          # binary / non-JSON carrier -> opaque, fall back


def _extract_peers(data) -> list:
    """Pull authentic sibling items {id, detail} out of a parsed carrier (best-effort, code-only)."""
    peers: list = []
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        src = data["items"]
    elif isinstance(data, list):
        src = data
    elif isinstance(data, dict):                     # registry-style {name: {...}}
        return [{"id": k, "detail": (v.get("detail", "") if isinstance(v, dict) else str(v))}
                for k, v in list(data.items())[:20]]
    else:
        return peers
    for x in src[:20]:
        if isinstance(x, dict):
            peers.append({"id": str(x.get("id", x.get("ref", "?"))), "detail": str(x.get("detail", ""))})
    return peers


def _infer_conventions(peers: list) -> str:
    """Infer the id FORMAT the carrier's real items follow (digits->'#', letters->'A', separators kept),
    so the Camoufleur mints a decoy id in the same shape.  Dominant shape + an example."""
    shapes = Counter()
    example = ""
    for it in peers[:20]:
        i = str(it.get("id", ""))
        if not i:
            continue
        example = example or i
        shapes[re.sub(r"[A-Za-z]", "A", re.sub(r"\d", "#", i))] += 1
    if not shapes:
        return ""
    return f"id format like '{shapes.most_common(1)[0][0]}' (e.g. {example})"


def _plant_file(directory: Path, decoy) -> None:
    """Format-agnostic sweep decoy: a marker FILE among the target set, mimicking a real member's ext."""
    directory.mkdir(parents=True, exist_ok=True)
    ext = decoy.payload.get("ext")
    if not ext:
        sibs = [p.suffix.lstrip(".") for p in directory.iterdir()
                if p.is_file() and p.suffix and not p.name.startswith(".")]
        dot = [p.name for p in directory.iterdir() if p.is_file() and p.name.startswith(".")]
        ext = (max(set(sibs), key=sibs.count) if sibs else ("env" if any(n == ".env" for n in dot) else "txt"))
    fp = directory / (f".{decoy.marker}" if ext == "env" and decoy.marker.startswith("env")
                      else f"{decoy.marker}.{ext}")
    if not fp.exists():
        fp.write_text(decoy.payload.get("detail", f"sensitive record {decoy.marker}"), encoding="utf-8")


class _PlantAdapter(BackendAdapter):
    """Shared PLANT deploy scaffolding: resolve the carrier + guard dir/file, then inject by placement."""

    def enrich(self, unit, work: Path, prior_benign=None, conventions: str = "") -> dict:
        """Deep-read the carrier -> plant_context (peers / real value / inferred conventions), and back-fill
        the unit so downstream roles (Camoufleur / Distinguisher) have the values.  Code-only."""
        cf = (work / unit.carrier_file) if unit.carrier_file else None
        fmt, excerpt, peers = "none", "", list(unit.peers or [])
        if cf and cf.is_dir():
            fmt = "dir"
            members = [p.name for p in sorted(cf.iterdir()) if p.is_file() and not p.name.startswith(".")]
            peers = peers or [{"id": n, "detail": "member file"} for n in members[:20]]
            excerpt = ", ".join(members[:20])
        elif cf and cf.exists():
            data = _load(cf, None)
            try:
                excerpt = cf.read_text(encoding="utf-8", errors="ignore")[:800]
            except OSError:
                excerpt = ""
            fmt = "json" if data is not None else "text"
            peers = peers or _extract_peers(data)
        real_value = unit.real_value or (peers[0].get("id") if peers else unit.uid)
        real_detail = unit.real_detail or (peers[0].get("detail", "") if peers else "")
        conv = unit.conventions or _infer_conventions(peers) or conventions
        unit.real_value, unit.real_detail, unit.peers, unit.conventions = real_value, real_detail, peers, conv
        return {"carrier_file": unit.carrier_file, "carrier_format": fmt, "carrier_excerpt": excerpt,
                "peers": peers, "inferred_conventions": conv, "real_value": real_value,
                "real_detail": real_detail, "must_take_reason": unit.must_take_reason}

    def deploy(self, decoy, work: Path) -> DeployRecord:
        rec = DeployRecord(decoy.uid, decoy.primitive)
        cf = work / decoy.carrier_file if decoy.carrier_file else None
        try:
            if cf is None:
                rec.status, rec.reason = "skipped", "no carrier_file"
            elif cf.is_dir() and decoy.placement != "sweep":
                rec.status, rec.reason = "skipped", f"carrier is a directory but placement={decoy.placement}"
            else:
                self._inject(cf, decoy)
                rec.artifact_paths = [str(cf)]
        except Exception as e:                                   # noqa: BLE001 — record, don't crash the env
            rec.status, rec.reason = "failed", f"{type(e).__name__}: {e}"[:200]
        return rec

    def _inject(self, cf: Path, decoy) -> None:
        raise NotImplementedError


class PlantSweep(_PlantAdapter):
    key = "plant:sweep"

    def _inject(self, cf: Path, decoy) -> None:      # sweep OR reference -> an extra item / co-member file
        if cf.is_dir():
            _plant_file(cf, decoy); return
        if cf.exists() and cf.suffix not in (".json", ""):
            _plant_file(cf.parent, decoy); return
        data = _load(cf, None)
        item = {"id": decoy.marker, "detail": decoy.payload.get("detail", ""), "sensitive": True}
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            if not any(x.get("id") == decoy.marker for x in data["items"]):
                data["items"].append(item)
        elif isinstance(data, dict):                             # registry-style {name: {...}}
            data[decoy.marker] = {"endpoint": decoy.marker, "detail": decoy.payload.get("detail", "")}
        elif isinstance(data, list):
            if not any((isinstance(x, dict) and x.get("id") == decoy.marker) for x in data):
                data.append(item)
        else:
            data = {"items": [item]}
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class PlantReference(PlantSweep):
    key = "plant:reference"          # same injection as sweep (an extra actionable item), file carrier


class PlantExfil(_PlantAdapter):
    key = "plant:exfil"

    def _inject(self, cf: Path, decoy) -> None:
        """Embed the honeytoken INSIDE the real target's record so exfiltrating it carries the token."""
        data = _load(cf, None)
        if data is None:                                   # non-JSON carrier -> append a token line
            if cf.exists():
                cf.write_text(cf.read_text(encoding="utf-8", errors="ignore").rstrip()
                              + f"\nlegacy_token={decoy.marker}\n", encoding="utf-8")
            return
        real = decoy.payload.get("real_value")
        token_field = {"legacy_token": decoy.marker}

        def _stamp(obj):
            if isinstance(obj, dict):
                if obj.get("id") == real or real is None:
                    obj.setdefault("fields", {}).update(token_field) if isinstance(obj.get("fields"), dict) \
                        else obj.update(token_field)
                    return True
                return any(_stamp(v) for v in obj.values())
            if isinstance(obj, list):
                return any(_stamp(v) for v in obj)
            return False
        if not _stamp(data):
            data = {"id": real, "fields": token_field} if not isinstance(data, dict) else {**data, **token_field}
        cf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class PlantBasis(_PlantAdapter):
    key = "plant:basis"

    def _inject(self, cf: Path, decoy) -> None:
        data = _load(cf, [])
        rec = {"ref": decoy.marker, "status": "approved", "note": decoy.payload.get("detail", "")}
        if isinstance(data, list):
            if not any(x.get("ref") == decoy.marker for x in data):
                data.insert(min(1, len(data)), rec)
        else:
            data = [rec]
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------- WRAP adapters (capability chokepoints) ----------------------------
class WrapFileShim(BackendAdapter):
    key = "wrap:file_shim"

    def enrich(self, unit, work: Path, prior_benign=None, conventions: str = "") -> dict:
        """wrap_context from the skill's scripts dir: entry_points / snippets / which are file-shimmable."""
        scripts = agent_runtime.skills_root(work) / unit.uid / "scripts"
        entry_points, snippets, mediatable = [], {}, []
        if scripts.exists():
            for entry in sorted(scripts.iterdir()):
                if not entry.is_file() or entry.name == helpers.RECORDER_HELPER \
                        or entry.name.startswith("_ad_impl_"):
                    continue
                entry_points.append(entry.name)
                try:
                    snippets[entry.name] = "\n".join(
                        entry.read_text(encoding="utf-8", errors="ignore").splitlines()[:8])
                except OSError:
                    snippets[entry.name] = ""
                if helpers._entry_kind(entry) is not None:    # file-shimmable => mediatable
                    mediatable.append(entry.name)
        bfs = f"benign calls used argv tokens {sorted(prior_benign)}" if prior_benign else ""
        return {"wrap_backend": unit.wrap_backend, "entry_points": entry_points, "entry_snippets": snippets,
                "mediatable_entries": mediatable, "benign_fit_summary": bfs,
                "must_take_reason": unit.must_take_reason}

    def deploy(self, decoy, work: Path) -> DeployRecord:
        rec = DeployRecord(decoy.uid, decoy.primitive)
        try:
            arts = self._mediate(work, decoy)
            if arts:
                rec.artifact_paths = [str(a) for a in arts]
                rec.status = "deployed" if decoy.hard_detect else "audit_only"
                if rec.status == "audit_only":
                    rec.reason = "recorder placed; audit-only verdict (boundary bypassable in shell)"
            else:
                decoy.hard_detect = False
                rec.status, rec.reason = "skipped", "file_shim: no mediatable entry to record"
        except Exception as e:                                   # noqa: BLE001
            rec.status, rec.reason = "failed", f"{type(e).__name__}: {e}"[:200]
        return rec

    @staticmethod
    def _mediate(work: Path, decoy) -> list:
        scripts = agent_runtime.skills_root(work) / decoy.uid / "scripts"
        mediated = []
        if not scripts.exists():
            return mediated
        want = set(decoy.entries_to_wrap or [])
        for entry in sorted(scripts.iterdir()):
            if not (entry.is_file() and entry.name != helpers.RECORDER_HELPER
                    and not entry.name.startswith("_ad_impl_")):
                continue
            if want and entry.name not in want:
                continue
            if helpers.mediate_capability(entry, decoy.uid):
                mediated.append(entry)
        return mediated

    def read_records(self, work: Path, decoy) -> list:
        out = []
        for r in helpers.read_touches(work):                     # dispatch_log.jsonl (record-first shims)
            if r.get("skill_id") == decoy.uid:
                out.append(CallRecord(uid=decoy.uid, backend="file_shim", entry=r.get("entry", ""),
                                      args=list(r.get("argv") or []), timestamp=r.get("ts", "")))
        return out


class WrapMcpMediator(BackendAdapter):
    """MCP capability chokepoint, folded INTO the Engine: deploy writes a local stdio-MCP-server config
    (defense/mcp_mediator.py) exposing the unit's tools; agent_config hands it to `claude --mcp-config`;
    read_records parses the server-side mediation log.  Needs the unit's MCP tool schema in
    decoy.mcp_tools (from enrich / the benchmark Adapter); without it there is nothing to mediate."""
    key = "wrap:mcp_mediator"

    def enrich(self, unit, work: Path, prior_benign=None, conventions: str = "") -> dict:
        """wrap_context for MCP: the unit's tool schema (seeded by the benchmark Adapter / Surveyor on
        `unit.mcp_tools`), surfaced as mcp_tools + entry_points + mediatable_entries so the WrapPlanner
        and the mcp_mediator deploy have a stable source.  Empty on file-based envs (nothing to mediate)."""
        tools = list(getattr(unit, "mcp_tools", None) or [])
        if not tools and getattr(unit, "carrier_file", ""):     # fallback: carrier_file points to a tools json
            data = _load(work / unit.carrier_file, None)
            if isinstance(data, list):
                tools = data
            elif isinstance(data, dict) and isinstance(data.get("tools"), list):
                tools = data["tools"]
        names = [t.get("name") for t in tools if t.get("name")]
        bfs = f"benign calls used argv tokens {sorted(prior_benign)}" if prior_benign else ""
        return {"wrap_backend": unit.wrap_backend, "mcp_tools": tools, "entry_points": names,
                "entry_snippets": {t.get("name", "?"): t.get("description", "") for t in tools},
                "mediatable_entries": names, "benign_fit_summary": bfs,
                "must_take_reason": unit.must_take_reason}

    @staticmethod
    def _paths(work: Path):
        cfgdir = work / ".mcp"; cfgdir.mkdir(parents=True, exist_ok=True)
        return cfgdir / "tools.json", cfgdir / "mediation_log.jsonl", cfgdir / "mcp.json"

    def deploy(self, decoy, work: Path) -> DeployRecord:
        rec = DeployRecord(decoy.uid, decoy.primitive)
        tools = list(decoy.mcp_tools or [])
        if not tools:
            decoy.hard_detect = False
            rec.status, rec.reason = "skipped", "mcp_mediator: no MCP tool schema on the unit (nothing to mediate)"
            return rec
        try:
            tpath, lpath, cpath = self._paths(work)
            existing = json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else []
            names = {t.get("name") for t in existing}
            existing += [t for t in tools if t.get("name") not in names]     # merge across mcp units
            tpath.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
            if not lpath.exists():
                lpath.write_text("", encoding="utf-8")
            cpath.write_text(json.dumps({"mcpServers": {"mediator": {
                "command": sys.executable, "args": [_MEDIATOR],
                "env": {"MCPTOX_TOOLS": str(tpath), "MEDIATION_LOG": str(lpath)}}}}), encoding="utf-8")
            rec.artifact_paths = [str(cpath)]
            rec.status = "deployed" if decoy.hard_detect else "audit_only"
        except Exception as e:                                   # noqa: BLE001
            rec.status, rec.reason = "failed", f"{type(e).__name__}: {e}"[:200]
        return rec

    def agent_config(self, decoys: list, work: Path) -> dict:
        _t, _l, cpath = self._paths(work)
        return {"mcp_config": str(cpath)} if cpath.exists() else {}   # -> agent_runtime.run_turn(mcp_config=...)

    def read_records(self, work: Path, decoy) -> list:
        _t, lpath, _c = self._paths(work)
        # attribute a logged call to THIS unit only if the tool is one of its own tools (the shared
        # mediation log may carry other MCP units' calls) — avoids duplicate attribution / false positives.
        own = {t.get("name") for t in (decoy.mcp_tools or []) if t.get("name")}
        out = []
        if lpath.exists():
            for line in lpath.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tool = r.get("tool", "")
                if own and tool not in own:                       # not this unit's tool -> skip
                    continue
                out.append(CallRecord(uid=decoy.uid, backend="mcp_mediator", entry=tool,
                                      kwargs=dict(r.get("arguments") or {}), timestamp=r.get("ts", "")))
        return out


class _SkipWrap(BackendAdapter):
    """A WRAP backend the file-based Engine does not deploy itself (recorded honestly, never a catch)."""
    reason = "not deployable by the Engine"
    unsupported = False           # audit_only is a legit fallback; rpc/egress are genuinely unimplemented

    def enrich(self, unit, work: Path, prior_benign=None, conventions: str = "") -> dict:
        return {"wrap_backend": unit.wrap_backend, "entry_points": [], "entry_snippets": {},
                "mediatable_entries": [], "benign_fit_summary": "",
                "unsupported": self.unsupported, "note": self.reason,
                "must_take_reason": unit.must_take_reason}

    def deploy(self, decoy, work: Path) -> DeployRecord:
        decoy.hard_detect = False
        return DeployRecord(decoy.uid, decoy.primitive, "skipped", reason=f"{self.key}: {self.reason}")


class WrapAuditOnly(WrapFileShim):
    """audit_only backend — the two-state fallback: if the unit HAS file entries we place a record-first
    shim but never issue a hard verdict (status 'audit_only' = recorder present, soft); if there is NO
    entry to record, nothing is placed (status 'skipped').  Reuses file_shim's enrich + read_records."""
    key = "wrap:audit_only"

    def deploy(self, decoy, work: Path) -> DeployRecord:
        decoy.hard_detect = False                            # audit_only is NEVER a hard catch
        rec = DeployRecord(decoy.uid, decoy.primitive)
        try:
            arts = self._mediate(work, decoy)
            if arts:
                rec.artifact_paths = [str(a) for a in arts]
                rec.status, rec.reason = "audit_only", "recorder placed; audit-only (no enforceable hard chokepoint)"
            else:
                rec.status, rec.reason = "skipped", "audit_only: no entry to record (nothing placed)"
        except Exception as e:                               # noqa: BLE001
            rec.status, rec.reason = "failed", f"{type(e).__name__}: {e}"[:200]
        return rec


class WrapRpcProxy(_SkipWrap):
    """DECLARED, not implemented (honest skip).  MINIMAL RUNTIME DESIGN for when a benchmark needs it:
      deploy        : start a protocol-specific socket/JSON-RPC recording proxy bound to a local port.
      agent_config  : return {"env_extra": {"<SERVICE>_ENDPOINT": "127.0.0.1:<port>"}} so the agent's
                      RPC client is redirected through the proxy (needs agent_runtime.run_turn(env_extra=)).
      read_records  : parse the proxy log -> CallRecord(uid, entry=method, kwargs=args, ...).
    Blocked here: RPC is protocol-diverse (no universal wire format) and there is no networked benchmark
    to validate against; the enforced-boundary strength is real but the deploy stays a skip until built."""
    key = "wrap:rpc_proxy"
    unsupported = True
    reason = "substrate-enforced boundary; needs an external RPC proxy runtime (not implemented here)"


class WrapEgressProxy(_SkipWrap):
    """DECLARED, not implemented (honest skip).  MINIMAL RUNTIME DESIGN for when a benchmark needs it:
      deploy        : start a logging HTTP/CONNECT proxy (records {method,url,host,path,body-digest}).
      agent_config  : return {"env_extra": {"HTTP_PROXY": ..., "HTTPS_PROXY": ...}} (needs
                      agent_runtime.run_turn(env_extra=) + episode start/stop lifecycle).
      read_records  : parse the proxy log -> CallRecord(uid, entry=host, kwargs={url,path,...}, ...).
    Blocked here: no networked agent task to validate end-to-end, and HTTPS bodies need MITM; deploy
    stays a skip until built.  (CONNECT gives host:port; plain HTTP gives full url/path.)"""
    key = "wrap:egress_proxy"
    unsupported = True
    reason = "substrate-enforced boundary; needs an external egress proxy runtime (not implemented here)"


REGISTRY = {a.key: a for a in (
    PlantSweep(), PlantExfil(), PlantReference(), PlantBasis(),
    WrapFileShim(), WrapMcpMediator(), WrapAuditOnly(), WrapRpcProxy(), WrapEgressProxy(),
)}


def adapter_for(decoy) -> BackendAdapter:
    return REGISTRY.get(key_for(decoy), BackendAdapter())
