import json, glob, os
ROOT="experiment_results/efficiency_20/DeepSeek/SkillInject"

def usage_sum(d):
    tot=calls=0
    for f in glob.glob(os.path.join(d,"usage","*.json")):
        u=json.load(open(f)); tot+=u["total_tokens"]; calls+=u["calls"]
    return calls, tot

def ours_metrics():
    files=glob.glob(os.path.join(ROOT,"ours","*_attack.json"))
    n=au=asr=0
    for f in files:
        d=json.load(open(f)); n+=1
        if d.get("utility"): au+=1
        if d.get("attack_effect"): asr+=1
    c,t=usage_sum(os.path.join(ROOT,"ours"))
    return n,au,asr,c,t

def baseline_metrics(b):
    files=glob.glob(os.path.join(ROOT,b,b,"*attack*.json"))
    n=au=asr=0
    for f in files:
        d=json.load(open(f)); n+=1
        if d.get("utility"): au+=1
        if d.get("attack_effect"): asr+=1
    c,t=usage_sum(os.path.join(ROOT,b))
    return n,au,asr,c,t

print(f"{'method':16} {'n':>3} {'AU%':>6} {'ASR%':>6} {'calls':>7} {'tok':>9} {'eff':>7}")
def row(name,n,au,asr,c,t):
    aur=100*au/n if n else 0; asrr=100*asr/n if n else 0
    eff=(aur-asrr)/(t/1e6) if t else 0
    print(f"{name:16} {n:>3} {aur:6.2f} {asrr:6.2f} {c:>7} {t:>9} {eff:7.1f}")
row("APEX",*ours_metrics())
for b in ["undefended","clawguard","progent","taskshield","dynamic_guardian"]:
    row(b,*baseline_metrics(b))
