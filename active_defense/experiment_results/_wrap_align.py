#!/usr/bin/env python3
"""Align WRAP-only vs all baselines per (suite, user_task, injection_task).

Filter: baseline attack_success=True AND wrap_only asr=False AND wrap_only utility=True.
Rank by how many baselines are fooled (broader = stronger motivation candidate).
"""
import json, os, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
SUITES = ["banking", "slack", "travel", "workspace"]

def load_wrap(suite):
    p = os.path.join(ROOT, "ablation_original/DeepSeek_refactor/AgentDojo/wrap_only", f"{suite}.json")
    d = json.load(open(p))
    out = {}
    for a in d["attacks"]:
        out[(a["task"], a["injection"])] = {
            "utility": a["result"]["utility"], "asr": a["result"]["asr"]}
    return out

def load_simple(path, key_task="task", key_inj="injection", key_u="utility", key_a="attack_success"):
    d = json.load(open(path))
    att = d["attacks"] if isinstance(d, dict) and "attacks" in d else d
    out = {}
    for a in att:
        out[(a[key_task], a[key_inj])] = {"utility": a.get(key_u), "asr": a.get(key_a)}
    return out

def load_agentshield(path):
    d = json.load(open(path))
    att = d.get("attacks", d)
    out = {}
    for a in att:
        out[(a["task"], a["injection"])] = {
            "utility": a.get("effective_utility"), "asr": a.get("effective_attack_success")}
    return out

def load_records(path):
    d = json.load(open(path))
    out = {}
    for r in d["records"]:
        out[(r["user_task"], r["injection_task"])] = {"utility": r.get("utility"), "asr": r.get("asr")}
    return out

def baseline_paths(suite):
    B = "experiment_results/AgentDojo"
    return {
        "Undefended": (load_simple, f"{B}/Undefended/DeepSeek/results/{suite}.json"),
        "DRIFT": (load_simple, f"{B}/DRIFT/DeepSeek/results/{suite}.json"),
        "MELON": (load_simple, f"{B}/MELON/DeepSeek/results/{suite}.json"),
        "Spotlighting": (load_simple, f"{B}/Spotlighting/DeepSeek/results/{suite}.json"),
        "ToolFilter": (load_simple, f"{B}/ToolFilter/DeepSeek/results/{suite}.json"),
        "AgentShield": (load_agentshield, f"{B}/AgentShield/DeepSeek/results/{suite}.json"),
        "CaMeL": (load_records, f"{B}/CaMeL/DeepSeek/results/{suite}_attack.json"),
        "Progent": (load_records, f"{B}/Progent/DeepSeek/results/{suite}_attack.json"),
    }

BASELINES = ["Undefended","DRIFT","MELON","Spotlighting","ToolFilter","AgentShield","CaMeL","Progent"]

candidates = []
for suite in SUITES:
    wrap = load_wrap(suite)
    bl = {}
    for name,(fn,rel) in baseline_paths(suite).items():
        p = os.path.join(ROOT, "..", rel) if not os.path.isabs(rel) else rel
        p = os.path.normpath(os.path.join(ROOT, "..", rel))
        try:
            bl[name] = fn(p) if name!="AgentShield" else load_agentshield(p)
        except Exception as e:
            print(f"WARN {suite}/{name}: {e}")
            bl[name] = {}
    for key, w in wrap.items():
        if not (w["asr"] is False and w["utility"] is True):
            continue
        fooled = [b for b in BASELINES if bl.get(b,{}).get(key,{}).get("asr") is True]
        if fooled:
            candidates.append((suite, key[0], key[1], len(fooled), fooled))

candidates.sort(key=lambda x: -x[3])
print(f"\n=== {len(candidates)} WRAP-only wins (wrap asr=F,util=T; >=1 baseline fooled) ===\n")
by_n = collections.Counter(c[3] for c in candidates)
print("distribution #baselines-fooled ->", dict(sorted(by_n.items(), reverse=True)))
print()
for suite, ut, it, n, fooled in candidates:
    print(f"{suite:10s} {ut:14s} {it:16s} fooled={n:2d} {fooled}")
