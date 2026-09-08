#!/usr/bin/env python3
"""Category-level WRAP necessity.

For each AgentDojo WRAP clean-win case, collapse baselines into 3 categories:
  policy      = {Progent, ToolFilter, AgentShield}
  provenance  = {CaMeL}
  alignment   = {DRIFT, MELON, Spotlighting}
A category "SECURES" a case if ANY member is clean-win (asr=F & util=T).
A category is "FOOLED" if ANY member has asr=True.
A category "overblocks-only" if it neither secures nor is fooled (all overblock/na).

We want cases where WRAP secures but as many categories as possible fail to secure,
and ideally at least one category is actually FOOLED (true security gap).
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(ROOT, "AgentDojo"))
SUITES = ["banking","slack","travel","workspace"]
CAT = {"Progent":"policy","ToolFilter":"policy","AgentShield":"policy",
       "CaMeL":"provenance",
       "DRIFT":"alignment","MELON":"alignment","Spotlighting":"alignment"}

def load_wrap(s):
    d=json.load(open(os.path.join(ROOT,"ablation_original/DeepSeek_refactor/AgentDojo/wrap_only",f"{s}.json")))
    return {(a["task"],a["injection"]):{"util":a["result"]["utility"],"asr":a["result"]["asr"]} for a in d["attacks"]}
def load_simple(p):
    d=json.load(open(p)); att=d["attacks"] if isinstance(d,dict) else d
    return {(a["task"],a["injection"]):{"util":a.get("utility"),"asr":a.get("attack_success")} for a in att}
def load_as(p):
    d=json.load(open(p)); att=d.get("attacks",d)
    return {(a["task"],a["injection"]):{"util":a.get("effective_utility"),"asr":a.get("effective_attack_success")} for a in att}
def load_rec(p):
    d=json.load(open(p))
    return {(r["user_task"],r["injection_task"]):{"util":r.get("utility"),"asr":r.get("asr")} for r in d["records"]}
def paths(s):
    return {"Progent":(load_rec,f"{BASE}/Progent/DeepSeek/results/{s}_attack.json"),
            "ToolFilter":(load_simple,f"{BASE}/ToolFilter/DeepSeek/results/{s}.json"),
            "AgentShield":(load_as,f"{BASE}/AgentShield/DeepSeek/results/{s}.json"),
            "CaMeL":(load_rec,f"{BASE}/CaMeL/DeepSeek/results/{s}_attack.json"),
            "DRIFT":(load_simple,f"{BASE}/DRIFT/DeepSeek/results/{s}.json"),
            "MELON":(load_simple,f"{BASE}/MELON/DeepSeek/results/{s}.json"),
            "Spotlighting":(load_simple,f"{BASE}/Spotlighting/DeepSeek/results/{s}.json")}

rows=[]
for s in SUITES:
    wrap=load_wrap(s); bl={}
    for n,(fn,rel) in paths(s).items():
        try: bl[n]=fn(rel)
        except Exception as e: print("WARN",s,n,e); bl[n]={}
    for key,w in wrap.items():
        if not (w["asr"] is False and w["util"] is True): continue
        catstat={}
        for cat in ["policy","provenance","alignment"]:
            members=[n for n,c in CAT.items() if c==cat]
            recs=[bl[m].get(key) for m in members]
            recs=[r for r in recs if r and r.get("asr") is not None]
            secured=any(r["asr"] is False and r.get("util") is True for r in recs)
            fooled=any(r["asr"] is True for r in recs)
            catstat[cat]=("secure" if secured else ("fooled" if fooled else "overblock"))
        n_fail=sum(v!="secure" for v in catstat.values())
        n_fooled=sum(v=="fooled" for v in catstat.values())
        rows.append((s,key[0],key[1],n_fail,n_fooled,catstat))

# Best motivation: max categories failing, then max actually fooled
rows.sort(key=lambda r:(-r[3],-r[4]))
print("\n=== AgentDojo: WRAP clean-wins ranked by how many defense CATEGORIES fail ===")
print("(policy=Progent/ToolFilter/AgentShield  provenance=CaMeL  alignment=DRIFT/MELON/Spotlighting)\n")
hdr=f"{'suite':9s} {'user':13s} {'inj':16s} nfail nfooled | policy      provenance  alignment"
print(hdr); print("-"*len(hdr))
for s,ut,it,nf,nfo,cs in rows[:30]:
    print(f"{s:9s} {ut:13s} {it:16s}  {nf}     {nfo}      | {cs['policy']:11s} {cs['provenance']:11s} {cs['alignment']}")
