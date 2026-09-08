#!/usr/bin/env python3
"""WRAP necessity finder.

For each case where WRAP-only is a clean-win (asr=False, util=True),
classify EVERY baseline as:
  fooled     : asr True
  overblock  : asr False but util False (stopped attack only by killing utility)
  clean-win  : asr False and util True
  na         : missing

Rank cases where WRAP is the ONLY clean-win across policy+provenance+alignment.
"""
import json, os, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(ROOT, "AgentDojo"))
SUITES = ["banking", "slack", "travel", "workspace"]

# category tags for narrative
CATEGORY = {
    "Undefended":"none",
    "Progent":"policy", "ToolFilter":"policy", "AgentShield":"policy",
    "CaMeL":"provenance",
    "DRIFT":"alignment", "MELON":"alignment", "Spotlighting":"alignment",
}

def load_wrap(suite):
    p = os.path.join(ROOT, "ablation_original/DeepSeek_refactor/AgentDojo/wrap_only", f"{suite}.json")
    d = json.load(open(p))
    return {(a["task"], a["injection"]): {"util": a["result"]["utility"], "asr": a["result"]["asr"]}
            for a in d["attacks"]}

def load_simple(path):
    d = json.load(open(path)); att = d["attacks"] if isinstance(d,dict) else d
    return {(a["task"], a["injection"]): {"util": a.get("utility"), "asr": a.get("attack_success")} for a in att}

def load_agentshield(path):
    d = json.load(open(path)); att = d.get("attacks", d)
    return {(a["task"], a["injection"]): {"util": a.get("effective_utility"), "asr": a.get("effective_attack_success")} for a in att}

def load_records(path):
    d = json.load(open(path))
    return {(r["user_task"], r["injection_task"]): {"util": r.get("utility"), "asr": r.get("asr")} for r in d["records"]}

def paths(suite):
    return {
        "Undefended": (load_simple, f"{BASE}/Undefended/DeepSeek/results/{suite}.json"),
        "DRIFT": (load_simple, f"{BASE}/DRIFT/DeepSeek/results/{suite}.json"),
        "MELON": (load_simple, f"{BASE}/MELON/DeepSeek/results/{suite}.json"),
        "Spotlighting": (load_simple, f"{BASE}/Spotlighting/DeepSeek/results/{suite}.json"),
        "ToolFilter": (load_simple, f"{BASE}/ToolFilter/DeepSeek/results/{suite}.json"),
        "AgentShield": (load_agentshield, f"{BASE}/AgentShield/DeepSeek/results/{suite}.json"),
        "CaMeL": (load_records, f"{BASE}/CaMeL/DeepSeek/results/{suite}_attack.json"),
        "Progent": (load_records, f"{BASE}/Progent/DeepSeek/results/{suite}_attack.json"),
    }

def classify(rec):
    if rec is None or rec.get("asr") is None: return "na"
    if rec["asr"] is True: return "fooled"
    if rec.get("util") is True: return "clean-win"
    return "overblock"

ORDER = ["Undefended","Progent","ToolFilter","AgentShield","CaMeL","DRIFT","MELON","Spotlighting"]
rows = []
for suite in SUITES:
    wrap = load_wrap(suite)
    bl = {}
    for name,(fn,rel) in paths(suite).items():
        try: bl[name] = fn(rel)
        except Exception as e: print("WARN",suite,name,e); bl[name]={}
    for key,w in wrap.items():
        if not (w["asr"] is False and w["util"] is True): continue
        cls = {b: classify(bl.get(b,{}).get(key)) for b in ORDER}
        # only interesting if at least one real defense baseline is fooled
        real = [b for b in ORDER if b!="Undefended"]
        n_fooled = sum(cls[b]=="fooled" for b in real)
        n_clean = sum(cls[b]=="clean-win" for b in real)
        # WRAP-necessity score: no real baseline achieves clean-win
        wrap_unique = (n_clean == 0)
        rows.append((suite,key[0],key[1],n_fooled,n_clean,wrap_unique,cls))

# strongest: wrap_unique True, then by n_fooled
rows.sort(key=lambda r:(not r[5], -r[3]))
uniq = [r for r in rows if r[5]]
print(f"\n=== {len(rows)} WRAP clean-wins total; {len(uniq)} where NO real baseline achieves clean-win ===\n")
print("Legend: F=fooled O=overblock C=clean-win .=na  (order:",ORDER,")\n")
for suite,ut,it,nf,nc,uq,cls in rows[:40]:
    tag="  <== WRAP-UNIQUE" if uq else ""
    short={ "fooled":"F","overblock":"O","clean-win":"C","na":"." }
    line=" ".join(f"{b[:4]}:{short[cls[b]]}" for b in ORDER)
    print(f"{suite:9s} {ut:13s} {it:16s} nf={nf} nc={nc} | {line}{tag}")
