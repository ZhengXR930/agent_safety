"""Progent on AgentDojo (finish the head-to-head): same suite + tasks + agent model as our run, but with
Progent enabled (policy-gen + enforce) via env, measuring residual ASR (AgentDojo `security`)."""
import argparse, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.task_suite.load_suites import get_suites
try:
    from secagent import reset_security_policy
except Exception:
    reset_security_policy=lambda *a,**k: None
ap=argparse.ArgumentParser(); ap.add_argument("--suite",default="banking"); ap.add_argument("--model",default="gpt-4o-mini-2024-07-18")
ap.add_argument("--attack",default="important_instructions"); ap.add_argument("--n-user",type=int,default=3)
a=ap.parse_args()
suite=get_suites("v1")[a.suite]
pipeline=AgentPipeline.from_config(PipelineConfig(llm=a.model,defense=None,system_message_name=None,system_message=None))
attacker=load_attack(a.attack,suite,pipeline)
print("="*80); print(f"  PROGENT on AgentDojo | {a.suite} | agent={a.model} | Progent ENABLED"); print("="*80,flush=True)
rows=[]
for ut in list(suite.user_tasks.values())[:a.n_user]:
    for itid in suite.injection_tasks:
        it=suite.get_injection_task_by_id(itid)
        try: reset_security_policy()
        except Exception: pass
        inj=attacker.attack(ut,it)
        try:
            util,sec=suite.run_task_with_pipeline(pipeline,ut,it,inj)
        except Exception as e:
            util,sec=False,False; print("  ERR",ut.ID,itid,str(e)[:80])
        rows.append({"user":ut.ID,"inj":itid,"asr":bool(sec),"utility":bool(util)})
        print(f"    {ut.ID} x {itid} | progent_asr={int(bool(sec))} util={int(bool(util))}",flush=True)
n=len(rows) or 1
print("-"*80); print(f"  Progent residual ASR = {sum(r['asr'] for r in rows)}/{len(rows)} ({sum(r['asr'] for r in rows)/n*100:.0f}%)")
out=HERE.parent/"experiment_stage"/f"agentdojo_progent_{a.suite}_{a.model}.json"
out.write_text(json.dumps({"rows":rows},indent=2)); print("  Saved:",out,flush=True)
