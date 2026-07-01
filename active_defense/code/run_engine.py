"""Driver for the GENERIC engine: read a benchmark via its (thin) Adapter, run the whole scheme.

    perceive (autonomous unit + must-take routing) -> design (Camoufleur + memory-backed Distinguisher)
        -> deploy (generic by must-take) -> run attack/benign -> OUTCOME detect -> metrics

No dataset-specific perceive/deploy/detect — only the Adapter knows the benchmark.
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
from defense.adapters_scr import (CapFlowAdapter, AuthBlurAdapter, TrustLiftAdapter,  # noqa: E402
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
    raise ValueError(a.benchmark)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True,
                    choices=["capflow", "authblur", "trustlift", "skillinject"])
    ap.add_argument("--cases-dir", required=True); ap.add_argument("--scripts-dir")
    ap.add_argument("--condition", default="A+B_explicit")
    ap.add_argument("--model", default="deepseek-chat"); ap.add_argument("--perceive-model", default="deepseek-chat")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=200); ap.add_argument("--certify-trials", type=int, default=8)
    ap.add_argument("--calib-runs", type=int, default=1, help="benign-fit calibration episodes per env")
    ap.add_argument("--no-fp-holdout", action="store_true",
                    help="cost lever: skip the extra held-out benign run (FP reported as n/a)")
    ap.add_argument("--observe-output", action="store_true",
                    help="ACCESS observation: also flag a decoy referenced in the agent's output")
    args = ap.parse_args()

    adapter = build_adapter(args)
    engine = Engine(client=client_for_model(args.perceive_model), model=args.model,
                    perceive_model=args.perceive_model, timeout=args.timeout,
                    certify_trials=args.certify_trials, calib_runs=args.calib_runs,
                    fp_holdout=not args.no_fp_holdout, observe_output=args.observe_output)
    print("=" * 78)
    print(f"  GENERIC ENGINE | {adapter.name} | limit={args.limit or 'all'} workers={args.workers} | {args.model}")
    print("=" * 78, flush=True)
    res = engine.evaluate(adapter, limit=args.limit, workers=args.workers)
    m = res["metrics"]
    for r in res["rows"]:
        if "error" in r:
            print(f"  {r['env']:>8} | ERROR {r['error']}")
        else:
            print(f"  {r['env']:>8} | units={r['n_units']} cand={r.get('n_candidates','?')} "
                  f"withheld={r.get('n_withheld_benignfit','?')} deployed={r['n_decoys']} | "
                  f"atk_acted={int(r['attack_acted'])} caught={int(r['caught'])} | fp={int(r['fp'])}")
    print("-" * 78)
    for k in ["n_envs", "n_errors", "attack_acted_rate", "caught_rate", "caught_given_acted", "fp_rate"]:
        v = m[k]
        print(f"  {k:22}: {v:.3f}" if isinstance(v, float) else f"  {k:22}: {v}")
    print("=" * 78)
    out = HERE.parent / "experiment_stage" / f"engine_{adapter.name}_{args.model}_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("  Saved:", out, flush=True)


if __name__ == "__main__":
    main()
