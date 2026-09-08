#!/usr/bin/env python3
"""Cross-baseline alignment for SkillInject: find cases where Ours secures
(attack_effect False & utility True) but baselines are fooled (attack_effect True)."""
import json, os, glob, collections

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense/experiment_results/SkillInject"
BASE={
 "Undefended":ROOT+"/Undefended/DeepSeek/undefended",
 "ClawGuard":ROOT+"/ClawGuard/DeepSeek/results",
 "Progent":ROOT+"/Progent/DeepSeek/results",
 "TaskShield":ROOT+"/TaskShield/DeepSeek/results",
 "Ours":ROOT+"/Ours/DeepSeek/results",
}
def key_from(fn):
    b=os.path.basename(fn)
    for suf in ["_clawguard","_progent","_taskshield","_clean","_attack",".json"]:
        b=b.replace(suf,"")
    return b  # idXXX_taskY
def load(dirp):
    out={}
    for fn in glob.glob(dirp+"/*attack*.json"):
        try: d=json.load(open(fn))
        except: continue
        k=key_from(fn)
        out[k]={"asr":bool(d.get("attack_effect")),"util":bool(d.get("utility")),
                "reason":d.get("attack_reason",""),"task":d.get("task","")}
    return out
data={b:load(p) for b,p in BASE.items()}
for b in data: print(b,"attack cases",len(data[b]))
ours=data["Ours"]
rows=[]
for k,o in ours.items():
    if not (o["asr"] is False and o["util"] is True): continue
    fooled=[b for b in ["Undefended","ClawGuard","Progent","TaskShield"] if data[b].get(k,{}).get("asr") is True]
    if fooled:
        rows.append((k,len(fooled),fooled,o["task"][:70]))
rows.sort(key=lambda r:-r[1])
print(f"\n=== {len(rows)} SkillInject cases: Ours secures, >=1 baseline fooled ===\n")
for k,n,f,t in rows:
    print(f"{k:20s} fooled={n} {f}  | {t}")
