"""Driver for the GENERIC engine: read a benchmark via its (thin) Adapter, run the whole scheme.

    Surveyor -> Enricher -> Camoufleur(PLANT)+Distinguisher(PLANT)/WrapPlanner(WRAP)
        -> TaskAllowance(WRAP) -> Deployer -> Detector -> Updater

All roles share ONE blackboard (EnvMemory); the Adapter is the ONLY env-specific code (where the env
is + the attack/benign task).  No dataset-specific perceive/deploy/detect.

The old harness/orchestrator/bindings/optimizer path has been removed (recoverable from git history).
The single active path is run_engine.py + defense/engine.py + defense/adapters.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from internal_client import client_for_model  # noqa: E402
from defense.engine import Engine  # noqa: E402
from defense.adapters import (CapFlowAdapter, AuthBlurAdapter, TrustLiftAdapter,  # noqa: E402
                              SkillInjectAdapter)


def build_adapter(a):
    if a.benchmark == "capflow":
        return CapFlowAdapter(Path(a.cases_dir), Path(a.scripts_dir) if a.scripts_dir else None,
                              condition=a.condition)
    if a.benchmark == "authblur":
        return AuthBlurAdapter(Path(a.cases_dir), Path(a.scripts_dir) if a.scripts_dir else None)
    if a.benchmark == "trustlift":
        return TrustLiftAdapter(Path(a.cases_dir))      # --cases-dir = the SCR-TrustLift root
    if a.benchmark == "skillinject":
        return SkillInjectAdapter(Path(a.cases_dir), n=a.limit or 8)   # --cases-dir = skill-inject root
    if a.benchmark == "agentdojo":
        from defense.agentdojo_backend import AgentDojoAdapter          # lazy: AgentDojo dep only when used
        return AgentDojoAdapter(a.suite, agent_model=a.agent_model, attack_name=a.attack,
                                n_user=a.n_user, n_inject=a.n_inject)
    raise ValueError(a.benchmark)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True,
                    choices=["capflow", "authblur", "trustlift", "skillinject", "agentdojo"])
    ap.add_argument("--cases-dir", default="")           # not needed for agentdojo (its env is in-process)
    ap.add_argument("--scripts-dir")
    ap.add_argument("--condition", default="A+B_explicit")
    # ---- agentdojo-only ----
    ap.add_argument("--suite", default="banking", help="agentdojo suite: banking|slack|travel|workspace")
    ap.add_argument("--agent-model", default="gpt-4o-mini-2024-07-18",
                    help="agentdojo: the BENCHMARK agent (separate from --model = our design roles)")
    ap.add_argument("--attack", default="important_instructions", help="agentdojo attack name")
    ap.add_argument("--n-user", type=int, default=0, help="agentdojo: cap user tasks (0=all)")
    ap.add_argument("--n-inject", type=int, default=0, help="agentdojo: cap injection tasks (0=all)")
    ap.add_argument("--model", default="deepseek-chat"); ap.add_argument("--perceive-model", default="deepseek-chat")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=200); ap.add_argument("--certify-trials", type=int, default=8)
    ap.add_argument("--calib-runs", type=int, default=1, help="benign-fit calibration episodes per env")
    ap.add_argument("--no-fp-holdout", action="store_true",
                    help="cost lever: skip the extra held-out benign run (FP reported as n/a)")
    ap.add_argument("--observe-output", action="store_true",
                    help="ACCESS observation: also flag a decoy referenced in the agent's output")
    ap.add_argument("--enforce", "--block", dest="enforce", action="store_true",
                    help="RESPONSE: at an enforced chokepoint, DENY an off-scope/honeytoken crossing live "
                         "(block==detect), not just record it.  Sound only for function-call/MCP/sandbox "
                         "substrates; open-shell stays detection-only.")
    ap.add_argument("--audit", dest="audit", action="store_true",
                    help="RESPONSE (deception, final scheme): instead of blocking a detected attack crossing, "
                         "return a FAKE success (real tool not run) so the attacker believes it worked and the "
                         "defense stays hidden.  Implies --enforce (policy active).")
    ap.add_argument("--no-provenance", dest="provenance", action="store_false",
                    help="ABLATION: disable trusted-read provenance (WRAP in-scope completeness).  Default on: "
                         "a crossing target the agent resolved at runtime from a trusted first-party read is "
                         "in-scope (allow-only, laundering-proof).  Off => higher benign FP; security unchanged.")
    ap.set_defaults(provenance=True)
    ap.add_argument("--runtime-benign", type=int, default=0,
                    help="runtime update: # online benign episodes folded via the Updater after deploy "
                         "(online benign-fit self-correction) before the attack")
    ap.add_argument("--runtime-tau", type=float, default=0.0,
                    help="Updater: allowed live benign touch rate before a decoy is withheld")
    ap.add_argument("--runtime-store", default="",
                    help="dir to PERSIST the per-scope benign profile across runs (warm-start + survive restart)")
    args = ap.parse_args()

    adapter = build_adapter(args)
    engine = Engine(client=client_for_model(args.perceive_model), model=args.model,
                    perceive_model=args.perceive_model, timeout=args.timeout,
                    certify_trials=args.certify_trials, calib_runs=args.calib_runs,
                    fp_holdout=not args.no_fp_holdout, observe_output=args.observe_output,
                    enforce=args.enforce, audit=args.audit, provenance=args.provenance,
                    runtime_benign=args.runtime_benign, runtime_tau=args.runtime_tau,
                    runtime_store=args.runtime_store)
    if args.benchmark == "agentdojo":                    # swap in the function-call substrate + its agent
        engine.runtime = adapter.backend
    print("=" * 78)
    print(f"  GENERIC ENGINE | {adapter.name} | limit={args.limit or 'all'} workers={args.workers} | {args.model}")
    print("=" * 78, flush=True)
    res = engine.evaluate(adapter, limit=args.limit, workers=args.workers)
    m = res["metrics"]
    for r in res["rows"]:
        if "error" in r:
            print(f"  {r['env']:>8} | ERROR {r['error']}")
        else:
            fp = r['fp']
            fp_s = "NA" if fp is None else str(int(fp))       # fp=None when --no-fp-holdout
            print(f"  {r['env']:>8} | units={r['n_units']} cand={r.get('n_candidates','?')} "
                  f"withheld={r.get('n_withheld_benignfit','?')} deployed={r['n_decoys']} | "
                  f"atk_acted={int(r['attack_acted'])} caught={int(r['caught'])} | fp={fp_s}")
    print("-" * 78)
    for k in ["n_envs", "n_errors", "attack_acted_rate", "caught_rate", "caught_given_acted", "fp_rate"]:
        v = m[k]
        print(f"  {k:22}: {v:.3f}" if isinstance(v, float) else f"  {k:22}: {v}")
    print("=" * 78)
    # AgentDojo: the per-(user_task x injection_task) rows carry the head-to-head metric (ASR + our
    # detection).  ONE deployment per suite is reused across every row (the attack-agnostic claim).
    adj = [row for r in res["rows"] if r.get("agentdojo_rows") for row in r["agentdojo_rows"]]
    if adj:
        succ = [x for x in adj if x["asr"]]
        n = len(adj) or 1
        enforced = any(x.get("blocked") is not None for x in adj) and args.enforce
        util_n = sum(x["utility"] for x in adj)
        print(f"  AGENTDOJO (through the generic Engine + real Detector){' + ENFORCE' if args.enforce else ''}:")
        print(f"    episodes            = {len(adj)}  (one deployment/suite reused across all)")
        print(f"    ASR (attack success)= {sum(x['asr'] for x in adj)}/{len(adj)} ({sum(x['asr'] for x in adj)/n*100:.0f}%)")
        print(f"    utility (task done) = {util_n}/{len(adj)} ({util_n/n*100:.0f}%)")
        print(f"    caught | success    = {sum(x['caught'] for x in succ)}/{len(succ)} "
              f"({(sum(x['caught'] for x in succ)/len(succ)*100) if succ else 0:.0f}%)")
        print(f"      of which WRAP={sum(x['wrap_caught'] for x in succ)} PLANT={sum(x['plant_caught'] for x in succ)}")
        if args.enforce:                                    # RESPONSE: crossings DENIED live (prevention)
            blk = [x for x in adj if x.get("blocked")]
            print(f"    BLOCKED (denied)    = {sum(x.get('n_blocked', 0) for x in adj)} calls "
                  f"across {len(blk)}/{len(adj)} episodes")
        # CLEAN benign FP: no-injection episodes with the policy ACTIVE.  Any block here is a genuine
        # false positive (WRAP/Evidence over-blocking a legit action, or a residual PLANT), and the
        # utility here is the no-attack utility UNDER defense.  This is the FP `fp=` above does NOT cover.
        bfp = [row for r in res["rows"] if r.get("benign_fp_rows") for row in r["benign_fp_rows"]]
        if bfp:
            nb = len(bfp)
            fp_ep = [x for x in bfp if x.get("blocked")]
            bu = sum(x["utility"] for x in bfp)
            print(f"    benign FP (no-atk)  = {len(fp_ep)}/{nb} ({len(fp_ep)/nb*100:.0f}%) episodes had a "
                  f"legit call BLOCKED  [WRAP/Evidence/PLANT false positive]")
            print(f"    benign utility(def) = {bu}/{nb} ({bu/nb*100:.0f}%)  (no-attack utility under defense)")
            if fp_ep:
                rs = [rr for x in fp_ep for rr in (x.get("blocked_reasons") or [])][:4]
                print(f"      FP reasons (sample): {rs}")
        print("=" * 78)
    tag = f"{adapter.name}_{args.suite}" if args.benchmark == "agentdojo" else adapter.name
    out = HERE.parent / "experiment_stage" / f"engine_{tag}_{args.model}_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("  Saved:", out, flush=True)


if __name__ == "__main__":
    main()
