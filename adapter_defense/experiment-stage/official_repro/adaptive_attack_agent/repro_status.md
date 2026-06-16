# AdaptiveAttackAgent Official Reproduction Status

Date: 2026-06-11

## Source

- Official repo present at `benchmarks/AdaptiveAttackAgent`.
- Official entrypoint: `python run.py --model <model_path> --defense <defense> --data_setting <base_subset|base|enhanced>`.
- Official attack algorithms available: `GCG`, `MGCG_ST`, `MGCG_DT`, `TGCG`.

## Startup Check

Command:

```bash
set -a; source ../../config.txt; set +a; python run.py --help
```

Result: succeeds.

## Current Blocker / 2026-06-11 Update

The official script derives `base_model = args.model.split('/')[-1]`. We will use only:

- `Llama-3.1-8B-Instruct`

The current repository does not contain a persistent local directory for this model yet. A full official run therefore needs:

- a local `Llama-3.1-8B-Instruct` path;
- an approved download/cache setup for that model.

Download attempt on A800 worker `3899170`:

- `huggingface-cli` is deprecated on the worker; `hf download` must be used.
- Worker proxy env has IPv6 entries in `NO_PROXY/no_proxy` that break `httpx`; clear only `NO_PROXY/no_proxy`, keep HTTP/HTTPS proxy.
- Downloading to the NFS repo path failed after full transfer due `.incomplete` rename/cache race.
- Downloading to worker local disk `/mnt/local/localcache00/agent_safety_models/vicuna-7b-v1.5` progressed, but the worker became unavailable (`worker ... not found`) before a final persistent verification could be completed.
- This Vicuna path is now retired. Active model choice is `Llama-3.1-8B-Instruct`.
- Reusable active script: `code/download_adaptive_attack_agent_llama31.sh`.

## Decision

Do not replace the official GCG/MGCG/TGCG algorithm with a lite rewrite. Until a durable `Llama-3.1-8B-Instruct` path is verifiably available on an active worker, use ASB official rollout and policy official baselines for immediate system experiments, and keep AdaptiveAttackAgent as an official-code baseline blocked on durable model assets / active worker availability.
