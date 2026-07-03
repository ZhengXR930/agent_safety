"""ExecutionBackend — the pluggable EXECUTION SUBSTRATE for the Engine (roles/method are substrate-agnostic).

The scheme (Surveyor -> Enricher -> Camoufleur/Distinguisher/WrapPlanner -> TaskAllowance -> Detector) is
generic.  What differs per benchmark is the SUBSTRATE it runs on:
  * how the survey/enrich surface is MATERIALIZED (a real case dir, or a synthesized snapshot of a
    function-call env);
  * how the target agent is RUN and how its committed effect + capability CALLS are observed.

This module isolates exactly those three substrate operations behind `ExecutionBackend`, so the same
Engine drives BOTH a filesystem/CLI benchmark and a function-call benchmark that ships its own agent.
The DEFENSE and the benchmark's AGENT are therefore fully separated: `engine.model` drives OUR design
roles; the backend picks the agent that actually runs the benchmark.

  * FileBackend      — the original path: isolated case dir + claude->deepseek CLI agent + file snapshot.
                       Extracted VERBATIM so the file-based benchmarks (CapFlow/AuthBlur/TrustLift/
                       SkillInject) behave exactly as before.
  * AgentDojoBackend — a function-call env: materialize tools+env as a snapshot for the file-based
                       Surveyor/Enricher, then run AgentDojo's OWN agent, intercept FunctionsRuntime for
                       CallRecords, synthesize the committed effect, and call the UNCHANGED Detector.
                       (see defense/agentdojo_backend.py)
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from . import agent_runtime
from .backend_adapters import adapter_for
from .detector import Detector


class ExecutionBackend:
    """The substrate seam.  Default = the file/CLI behavior (FileBackend); AgentDojoBackend overrides."""

    # 1. survey/enrich SURFACE — a work dir the Surveyor (LLM) explores and the Enricher reads carriers from.
    @contextmanager
    def survey_context(self, env, engine):
        raise NotImplementedError

    # 1b. Surveyor DELIVERY (same _SURVEY prompt / model; substrate chooses HOW it reaches the LLM).
    #     Default = a claude-CLI session that EXPLORES the work dir (file benchmarks).  A structured env
    #     (AgentDojo) overrides with an API call carrying the surface as CONTEXT (knowledge, not exploration).
    def survey_session(self, work, engine):
        from .subagent import Session
        return Session("Surveyor", work, engine.perceive_model, timeout=engine.timeout)

    # 2. per-unit enrich dispatch (default: the unit's BackendAdapter reads its carrier under `work`).
    def enrich_unit(self, unit, work: Path, prior_benign, conventions: str) -> dict:
        return adapter_for(unit).enrich(unit, work, prior_benign, conventions=conventions)

    # 3a. post-perceive normalization hook (an ENVIRONMENT FACT the backend knows, not a method judgment).
    def post_perceive(self, mem, env) -> None:
        return None

    # 3b. run ONE episode: deploy decoys -> run the agent -> observe effect+calls -> Detector.detect.
    def episode(self, engine, env, decoys: list, mode: str, real_values=(), benign_argv=None,
                wrap_hard: bool = True, task_contract=None) -> dict:
        raise NotImplementedError


class FileBackend(ExecutionBackend):
    """The original file/CLI substrate: an isolated case DIR + the claude->deepseek CLI agent + a
    filesystem snapshot for the produced effect.  This is a faithful extraction of the previous
    Engine.perceive/enrich/episode bodies — behavior is unchanged for the file-based benchmarks."""

    @contextmanager
    def survey_context(self, env, engine):
        with agent_runtime.isolated_env(env.case_dir) as work:
            yield work

    def episode(self, engine, env, decoys: list, mode: str, real_values=(), benign_argv=None,
                wrap_hard: bool = True, task_contract=None) -> dict:
        # attack/benign may live in DIFFERENT dirs (e.g. TrustLift experiment vs control); else same dir.
        case_dir = env.case_dir if (mode == "attack" or not env.benign_case_dir) else env.benign_case_dir
        with agent_runtime.isolated_env(case_dir) as work:
            dep = engine.deploy(work, decoys)
            # detect on ACTIVE decoys: a hard-verdict 'deployed' OR an 'audit_only' recorder (records
            # crossings, hard=False).  'skipped'/'failed' never had a recorder placed -> excluded.
            active_uids = {r.uid for r in dep if r.status in ("deployed", "audit_only")}
            active = [d for d in decoys if d.uid in active_uids]
            sb = work / "sandbox"; sb.mkdir(exist_ok=True)
            before = Detector.snapshot(sb)             # AFTER deploy: decoy carriers are read-state
            task = engine._task_for(env, mode)
            # agent-invocation config from the active backends (e.g. an MCP --mcp-config) — this is how a
            # substrate backend like mcp_mediator is folded INTO the Engine instead of a separate runner.
            agent_cfg: dict = {}
            for ad in {adapter_for(d) for d in active}:
                agent_cfg.update(ad.agent_config(active, work))
            _, out, _ = agent_runtime.run_turn(task, work, engine.model, session_id=agent_runtime.new_session(),
                                               resume=False, timeout=engine.timeout, **agent_cfg)
            # gather runtime CallRecords uniformly from every active WRAP recorder (file_shim / mcp / ...).
            call_records = [r for d in active if d.primitive == "wrap"
                            for r in adapter_for(d).read_records(work, d)]
            result = Detector(observe_output=engine.observe_output).detect(
                work=work, sb=sb, before=before, out=out or "", env=env, mode=mode, decoys=active,
                call_records=call_records, real_values=real_values, benign_argv=benign_argv,
                task_contract=task_contract, wrap_hard=wrap_hard)
        return {"mode": mode, **result.to_dict(), "deploy": [r.to_dict() for r in dep]}
