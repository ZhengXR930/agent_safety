# MSB frozen-contract rerun

## Current status

- Benchmark: MCP Security Bench (MSB).
- Frozen attack cases: 622.
- Unique frozen contract keys: 22.
- Frozen contracts present: 22.
- Missing frozen contracts: 0.
- Benchmark-native PUA denominator: 415. The runner also records an all-case
  utility witness for all 622 attack cases.
- The repository integrity/registry check passes.
- The frozen-contract rerun completed all 622 attack cases with 622 unique case
  IDs and no missing scoring fields. Benchmark-native PUA is 400/415 (96.39\%)
  and ASR is 0/622 (0.00\%). The remaining 207 cases are attack constructions
  for which MSB defines PUA as unavailable, not utility failures.
- The final artifact is
  `active_defense/experiment_results/MSB/Ours/DeepSeek/msb_attack_rerun.json`.

The main Python environment is the Conda environment `msb-active-defense`
(Python 3.11). The official MSB source is under
`benchmarks/external/MSB`, and the reviewed contracts are under
`active_defense/code/ours/contracts/msb/contracts.json`.

## Runtime notes

Export `DEEPSEEK_API_KEY` in the shell before starting a new run.

The runner now relocates the frozen Linux MSB root to this checkout in memory
after selecting the frozen contract. It also resolves the upstream MCP config
placeholders and `uv` executable in memory. The frozen case manifest, contract
catalog, and installed LangChain package are not rewritten.

The official attack-tool environment has been synchronized from its frozen
`uv.lock` into `benchmarks/external/MSB/data/tools/attack_tools/.venv`.
Terminal, Filesystem, DuckDuckGo, Flux, and Word MCP servers have all passed a
real initialization/list-tools probe without making a model call.
The 30 PubMed and 20 Memory cases use the local server implementations shipped
inside MSB instead of Smithery's remote endpoints, which now require browser
OAuth.

PLANT placement now uses a per-key concurrent cache: identical requests share
one in-flight model call while distinct keys can run in parallel. Completed
entries are appended to `msb_attack_rerun.plant-cache.jsonl` and survive
restart. Pending MSB jobs are round-robin interleaved by frozen-contract key so
four workers do not queue on the same placement keys. The attack-tool virtual
environment also includes the upstream scripts' `pandas` dependency.

For a local unattended continuation, run `./run_msb_local.sh`. It prompts for
the key without echoing it, detects the existing checkpoint, and adds resume
flags to both runner layers. Set `MSB_WORKERS` to override the default of 4.

## Checks already run

From `active_defense/`:

```bash
PYTHONNOUSERSITE=1 /opt/anaconda3/envs/msb-active-defense/bin/python \
  -m code.run --verify-only \
  --benchmark msb --method ours \
  --target-model deepseek-v4-flash \
  --defense-model deepseek-v4-flash \
  --output /tmp/msb-verify.json -- \
  --mode attack --frozen-contracts-only
```

The one-case command also reaches the expected preflight failure
`Missing DEEPSEEK_API_KEY` before any model or MCP-server work begins.

## Intended pilot and full run

After exporting the key, run a one-case pilot first:

```bash
conda activate msb-active-defense
cd /Users/zhengxinran/Documents/S2LAB/project/agent_safety/active_defense
PYTHONNOUSERSITE=1 python -m code.run \
  --benchmark msb --method ours \
  --target-model deepseek-v4-flash \
  --defense-model deepseek-v4-flash \
  --output experiment_results/MSB/Ours/DeepSeek/msb_attack_rerun.json \
  --workers 1 -- \
  --mode attack --msb-limit 1 --frozen-contracts-only
```

Then remove `--msb-limit 1` for all 622 attack cases. Use `--resume` on both
the outer runner and the MSB runner arguments when continuing an interrupted
run:

```bash
PYTHONNOUSERSITE=1 python -m code.run \
  --benchmark msb --method ours \
  --target-model deepseek-v4-flash \
  --defense-model deepseek-v4-flash \
  --output experiment_results/MSB/Ours/DeepSeek/msb_attack_rerun.json \
  --workers 1 --resume -- \
  --mode attack --frozen-contracts-only --resume
```

Each completed case is checkpointed. Its row contains the frozen contract,
WRAP/PLANT decisions, continuation/audit data, utility, PUA eligibility, and
official attack success. These fields are sufficient for the later overlapping
utility-error attribution.
