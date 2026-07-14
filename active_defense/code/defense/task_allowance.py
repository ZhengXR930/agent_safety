"""TaskAllowanceExtractor — a WRAP-only, task-level, memory-backed role.

Runs AFTER the WrapPlanner (env/unit-level) and BEFORE the target agent, once per user task.  It reads
ONLY the TRUSTED user task (plus a summary of the wrappable capabilities) and converts it into a
TASK CONTRACT: the concrete steps the user authorized, with the identity targets/sinks each step may
legitimately use.  It does NOT judge malice, and it does NOT read environment content / tool responses /
agent output / retrieved documents — so attacker-injected data can never widen the contract.

The Detector stays code-only: a WRAP crossing is allowed iff it matches the task contract OR fits the
benign-fit envelope (an OR); otherwise it is off-scope.  TaskAllowance authorizes the CURRENT task;
benign-fit authorizes the workflow's normal envelope (system params, templates, historical values).
They are complementary, never a substitute for each other.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class ContractStep:
    action: str = ""
    entries: list = field(default_factory=list)          # capability entries this step would invoke
    targets: list = field(default_factory=list)          # [{"role","value"}] objects operated on
    sinks: list = field(default_factory=list)            # [{"role","value"}] outgoing destinations
    evidence: str = ""                                   # the phrase in the task authorizing this step

    def to_dict(self) -> dict:
        return {"action": self.action, "entries": self.entries, "targets": self.targets,
                "sinks": self.sinks, "evidence": self.evidence}

    def values(self) -> set:
        return {str(x.get("value", "")) for x in (self.targets + self.sinks) if x.get("value")}


@dataclass
class TaskContract:
    steps: list = field(default_factory=list)            # list[ContractStep]

    def to_dict(self) -> dict:
        return {"steps": [s.to_dict() for s in self.steps]}

    def has_entry_info(self) -> bool:
        """True iff the contract named at least one concrete capability ENTRY (not just an action verb).
        The Detector only enforces the entry/action-level constraint when this holds — the no-entry
        fallback stays token-level because this extractor could not bind the task to concrete entries."""
        return any(s.entries for s in self.steps)

    def allowed_entries_for(self, uid: str | None = None, entries=None) -> set:
        """Entry/action names the task authorized (union across steps: each step's `entries` plus its
        `action` verb).  v1 is task-wide — an entry/action named in ANY step is authorized (the uid /
        entries args are accepted for a future step-scoped refinement).  Enables the Detector's
        entry/action-level constraint: a crossing whose entry the task never named (and benign-fit never
        saw) is off-scope even if it carries a task-authorized target token."""
        ents: set = set()
        for s in self.steps:
            ents |= {str(e) for e in s.entries}
            if s.action:
                ents.add(str(s.action))
        return ents

    def allowed_tokens_for(self, uid: str, entries=None) -> set:
        """RAW identity values the task authorizes for this unit/entry (the Detector normalizes them).

        v1 = conservative TOKEN-level: values from steps whose `entries` name this unit/entry; if the
        extractor named no matching entry, fall back to the identity values across ALL steps ("token
        appears in any step").  Step-level tuple matching can be added later without enumerating
        risk categories inside this extractor."""
        keys = {str(e) for e in (entries or [])} | {uid}
        matched = [s for s in self.steps if keys & {str(e) for e in s.entries}]
        pool = matched or self.steps
        vals: set = set()
        for s in pool:
            vals |= s.values()
        return vals


_EXTRACT = """You convert a TRUSTED user task into a TASK CONTRACT — the concrete steps the user
authorized.  You read ONLY the user task and the list of wrappable capabilities below.  You do NOT judge
malice, and you do NOT see any environment content, tool output, or documents.

User task:
{task}

Wrappable capabilities you may reference in `entries` (uid — description):
{units}

Break the task into ordered steps.  For each step:
- action: the short verb explicitly authorized by this step
- entries: which capability uids this step would invoke (subset of the list; may be empty)
- targets: objects the step operates on, each {{"role": "...", "value": "..."}}
- sinks: outgoing destinations, each {{"role": "...", "value": "..."}}
- evidence: the exact phrase in the task that authorizes this step

Only include values the user EXPLICITLY named.  Return ONLY JSON:
{{"steps": [{{"action": "...", "entries": [...], "targets": [...], "sinks": [...], "evidence": "..."}}]}}"""


class TaskAllowanceExtractor:
    def __init__(self, client, model: str):
        self.client, self.model = client, model

    def extract(self, user_task: str, mem) -> TaskContract:
        wrap_units = self._wrap_units(mem)
        if self.client is None:
            return self._fallback(user_task)
        # show entries_to_wrap so the LLM names the SPECIFIC entries it authorizes (the Detector's
        # entry-level check is per-entry — a unit-level uid alone is coarser than an explicit entry).
        listing = "\n".join(
            f"- {u['uid']} ({u['kind']}) — entries={u['entries_to_wrap']}; records={u['record_params']}; "
            f"reason={u['reason']}" for u in wrap_units
        ) or "(none)"
        try:
            data = self._ask_json(_EXTRACT.format(task=user_task or "", units=listing))
            steps = [self._step(s) for s in (data.get("steps") or []) if isinstance(s, dict)]
            return TaskContract(steps=steps) if steps else self._fallback(user_task)
        except Exception:                                    # noqa: BLE001 — extractor is best-effort
            return self._fallback(user_task)

    # ---- helpers ----
    @staticmethod
    def _wrap_units(mem) -> list:
        kinds = {u.uid: u.kind for u in getattr(mem, "units", [])}
        out = []
        for uid, pl in getattr(mem, "wrap_plans", {}).items():
            out.append({"uid": uid, "kind": kinds.get(uid, "tool"),
                        "entries_to_wrap": pl.get("entries_to_wrap", []),
                        "record_params": pl.get("record_params", []), "reason": pl.get("reason", "")})
        return out

    @staticmethod
    def _step(s: dict) -> ContractStep:
        def _ids(xs):
            return [{"role": str(x.get("role", "")), "value": str(x.get("value", ""))}
                    for x in (xs or []) if isinstance(x, dict) and x.get("value")]
        return ContractStep(action=str(s.get("action", "")),
                            entries=[str(e) for e in (s.get("entries") or [])],
                            targets=_ids(s.get("targets")), sinks=_ids(s.get("sinks")),
                            evidence=str(s.get("evidence", "")))

    def _fallback(self, user_task: str) -> TaskContract:
        """No-LLM fallback: no task contract rather than an enumerated heuristic contract."""
        return TaskContract(steps=[])

    def _ask_json(self, prompt: str) -> dict:
        from .sdk_session import SdkSession
        import re
        txt = SdkSession("TaskAllowance", model=self.model).ask(prompt)
        m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
        if m:
            txt = m.group(1)
        m = re.search(r"\{.*\}", txt, re.S)
        return json.loads(m.group(0)) if m else {}
