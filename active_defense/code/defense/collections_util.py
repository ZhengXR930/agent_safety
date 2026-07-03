"""Generic collection decomposition + honey injection for STRUCTURED-OBJECT environments.

Benchmark-AGNOSTIC (no per-suite, no AgentDojo knowledge).  A structured env (nested dict / pydantic
model) holds COLLECTIONS the attacker processes as a set — lists of records, registries of records,
lists of names.  For PLANT the generic scheme needs each such collection exposed as its OWN carrier so
the (unchanged) Surveyor emits one plant unit per collection, and the Camoufleur/Distinguisher design +
certify a decoy among THAT collection's real peers — exactly as they already do for a file benchmark
where each collection is a separate file.

This module provides that decomposition (structured object -> per-collection carrier files) and the
mirror operation for deploy (append a certified honey member into the LIVE collection, by path).  A
file benchmark keeps its real files; a structured-object backend (AgentDojo) calls these helpers.  The
per-suite `if bank_account ... elif filesystem ...` special-casing is gone: transactions, files,
channels, emails, hotels — all are just auto-discovered collections addressed by their path.
"""
from __future__ import annotations

import copy
import json
from collections import defaultdict
from pathlib import Path


def _scalar(v) -> bool:
    return isinstance(v, (str, int, float)) and str(v) != "" and not isinstance(v, bool)


def _is_numeric(vs) -> bool:
    return all(str(v).replace(".", "", 1).lstrip("-").isdigit() for v in vs)


def pick_marker_field(records) -> str | None:
    """The field whose values are most IDENTIFIER-LIKE — judged from DATA ALONE (uniqueness across the
    set × value length), with NO assumption about field names or value formats.  A sequential integer id
    (unique but tiny + numeric) loses to an IBAN / email / filename / MRN (unique + long).  Domain-agnostic
    by construction: it finds the honeytoken-bearing field on banking, email, logistics, medical, etc.
    equally, because it measures the data, not patterns we hard-coded."""
    cols = defaultdict(list)
    n = 0
    for r in records:
        if isinstance(r, dict):
            n += 1
            for k, v in r.items():
                if _scalar(v):
                    cols[k].append(str(v))
    n = n or 1
    best, best_score = None, -1.0
    for k, vs in cols.items():
        if len(vs) < 0.6 * n:                               # field present in most members
            continue
        uniqueness = len(set(vs)) / len(vs)                 # 1.0 = every member distinct
        avg_len = sum(len(v) for v in vs) / len(vs)
        score = uniqueness * min(avg_len, 40) * (0.25 if _is_numeric(vs) else 1.0)
        if score > best_score:
            best, best_score = k, score
    return best


def identity_of(rec, marker_field: str | None = None) -> str:
    """A member's identity value the decoy mimics: the collection's marker field if given, else the most
    distinctive scalar in THIS record (longest non-numeric), else any scalar.  No field-name assumptions."""
    if not isinstance(rec, dict):
        return str(rec)
    if marker_field and _scalar(rec.get(marker_field)):
        return str(rec[marker_field])
    scal = [str(v) for v in rec.values() if _scalar(v)]
    if scal:
        return max(scal, key=lambda s: (0 if s.replace(".", "", 1).isdigit() else 10) + min(len(s), 40))
    return "?"


def _summary_of(rec) -> str:
    """A RICH, faithful rendering of a real member (all scalar fields), so the Camoufleur designs a
    decoy against realistic content and the Distinguisher judges it against realistic peers — NOT a
    stripped 3-field summary (which unfairly makes content-rich members look thin and any decoy obvious)."""
    if not isinstance(rec, dict):
        return str(rec)[:300]
    bits = []
    for rk, rv in rec.items():
        if isinstance(rv, (str, int, float, bool)):
            bits.append(f"{rk}={rv}")
        elif isinstance(rv, list) and rv and isinstance(rv[0], (str, int, float)):
            bits.append(f"{rk}={list(rv)[:4]}")
    return "; ".join(bits)[:400]


def _is_record(x) -> bool:
    """A dict is a RECORD (a single item) if most of its values are scalars, not sub-collections."""
    if not isinstance(x, dict) or not x:
        return False
    scal = sum(1 for v in x.values() if isinstance(v, (str, int, float, bool)) or v is None)
    return scal >= max(1, len(x) // 2)


def _collection_kind(node):
    """Classify a node as a collection: 'list_rec' | 'list_str' | 'dict_rec', else None."""
    if isinstance(node, list) and len(node) >= 2:
        if all(isinstance(x, dict) for x in node):
            return "list_rec"
        if all(isinstance(x, str) for x in node):
            return "list_str"
    if isinstance(node, dict) and len(node) >= 2 and all(_is_record(v) for v in node.values()):
        return "dict_rec"
    return None


def decompose_collections(dump: dict, *, max_depth: int = 4, min_items: int = 2) -> list[dict]:
    """Walk a dumped structured object; return one descriptor per COLLECTION found (not recursing into a
    collection's members).  Each: {path, kind, peers:[{id,detail}], n}.  `path` is a dotted key path."""
    out: list[dict] = []

    def walk(node, path, depth):
        if depth > max_depth:
            return
        kind = _collection_kind(node)
        if kind is not None:
            if kind == "list_str":
                peers = [{"id": str(x), "detail": "member"} for x in node[:20]]
            else:                                            # list_rec | dict_rec
                members = node if kind == "list_rec" else list(node.values())
                mf = pick_marker_field(members)              # DATA-driven honeytoken field (no name/patterns)
                peers = [{"id": identity_of(m, mf), "detail": _summary_of(m)} for m in members[:20]]
            if len([p for p in peers if p["id"] and p["id"] != "?"]) >= min_items:
                out.append({"path": path, "kind": kind, "peers": peers, "n": len(node)})
            return                                           # do NOT recurse into collection members
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k), depth + 1)

    walk(dump, "", 0)
    return out


def carrier_name(path: str) -> str:
    """The survey carrier file for a collection path (under sandbox/)."""
    safe = path.replace("/", "_")
    return f"sandbox/col__{safe}.json"


def path_of_carrier(carrier_file: str) -> str | None:
    """Inverse of carrier_name: recover the dotted path from a carrier_file, or None if not one."""
    name = Path(carrier_file).name
    if not (name.startswith("col__") and name.endswith(".json")):
        return None
    return name[len("col__"):-len(".json")]


def materialize(sb_dir: Path, collections: list[dict]) -> None:
    """Write each collection's peer list as its own carrier file (list of {id, detail}), so the unchanged
    Surveyor/Enricher perceive one plant unit per collection and read its real peers."""
    for c in collections:
        (sb_dir / f"col__{c['path'].replace('/', '_')}.json").write_text(
            json.dumps(c["peers"], indent=2, ensure_ascii=False, default=str), encoding="utf-8")


# ---------------------------- deploy: append a honey member into a LIVE collection ----------------------------
def _resolve(root, path: str):
    """Navigate a LIVE object (pydantic attrs and/or dict keys) to the collection at `path`."""
    obj = root
    for part in path.split("."):
        if obj is None:
            return None
        obj = obj.get(part) if isinstance(obj, dict) else getattr(obj, part, None)
    return obj


def _as_dict(m):
    if isinstance(m, dict):
        return m
    if hasattr(m, "model_dump"):
        try:
            return m.model_dump()
        except Exception:  # noqa: BLE001
            return {}
    return vars(m) if hasattr(m, "__dict__") else {}


def _clone_with_marker(template, marker: str, marker_field: str | None):
    """Clone a real member (full schema -> indistinguishable) and stamp the honeytoken into the collection's
    DATA-chosen marker field, so exfiltrating / sweeping the collection carries the marker.  Works on dict
    records and pydantic models.  No field-name/pattern assumptions — `marker_field` came from data stats."""
    try:
        clone = copy.deepcopy(template)
    except Exception:  # noqa: BLE001
        return None, False
    present = False
    if isinstance(clone, dict):
        if marker_field and _scalar(clone.get(marker_field)):
            clone[marker_field] = marker if isinstance(clone[marker_field], str) else clone[marker_field]
            clone[marker_field] = marker; present = True
        clone["honey_ref"] = marker; present = True         # belt-and-suspenders: always detectable
    else:                                                    # pydantic model / attr object
        if marker_field:
            try:
                cur = getattr(clone, marker_field, None)
                if isinstance(cur, str):
                    setattr(clone, marker_field, marker); present = True
            except Exception:  # noqa: BLE001
                pass
        if not present:                                      # fall back to ANY string field so it's carried
            for k in list(getattr(type(clone), "model_fields", {}) or getattr(clone, "__dict__", {}).keys()):
                try:
                    if isinstance(getattr(clone, k), str):
                        setattr(clone, k, marker); present = True; break
                except Exception:  # noqa: BLE001
                    pass
    return clone, present


def embed_marker_in_members(root, path: str, marker: str, k: int = 3) -> bool:
    """EXFIL deploy: embed the honeytoken INTO existing real members (no new member added), so an attacker
    that reads/exfiltrates the real data carries the token — must-take by STRUCTURE, no indistinguishability
    certification needed (unlike SWEEP, which adds a member an enumerating attacker can always exclude).
    Stamps up to `k` members' longest string field (data-driven) so any exfil of the set carries it.
    Returns True iff at least one member was stamped."""
    col = _resolve(root, path)
    if col is None:
        return False
    members = col if isinstance(col, list) else (list(col.values()) if isinstance(col, dict) else None)
    if not members:
        return False
    done = 0
    for m in members[:k]:
        if isinstance(m, str):
            continue                                        # name lists: nothing to embed into
        d = _as_dict(m)
        field = max((kk for kk, vv in d.items() if isinstance(vv, str) and vv),
                    key=lambda kk: len(d[kk]), default=None)
        try:
            if isinstance(m, dict):
                if field:
                    m[field] = f"{m[field]} {marker}"
                else:
                    m["_note"] = marker
                done += 1
            elif field and isinstance(getattr(m, field, None), str):
                setattr(m, field, f"{getattr(m, field)} {marker}")
                done += 1
        except Exception:  # noqa: BLE001
            continue
    return done > 0


def inject_by_path(root, path: str, marker: str, detail: str = "") -> bool:
    """Append a certified honey member into the LIVE collection at `path`.  Returns True iff deployed (the
    marker is actually present in the appended member).  The marker field is chosen from the LIVE members'
    DATA (same algorithm as decompose), so no naming/format assumptions.  Generic over list/dict/name."""
    col = _resolve(root, path)
    if col is None:
        return False
    if isinstance(col, list):
        if not col:
            return False
        if isinstance(col[0], str):                          # list of names -> the marker IS the member
            if marker not in col:
                col.append(marker)
            return True
        mf = pick_marker_field([_as_dict(m) for m in col[:20]])
        clone, present = _clone_with_marker(col[0], marker, mf)
        if clone is None or not present:
            return False
        col.append(clone)
        return True
    if isinstance(col, dict):
        if not col:
            return False
        members = list(col.values())
        mf = pick_marker_field([_as_dict(m) for m in members[:20]])
        clone, present = _clone_with_marker(members[0], marker, mf)
        if clone is None or not present:
            return False
        col[marker] = clone
        return True
    return False
