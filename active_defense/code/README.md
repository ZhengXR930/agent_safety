# Evaluation architecture

Every benchmark owns exactly one frozen dataset, one adapter, and one evaluator.
All methods consume that same adapter; a baseline may not rewrite prompts,
attacks, tool schemas, case identities, or denominators.

```text
core/                    shared types, adapter/runner contracts and validation
benchmarks/<name>/       protocol.json, data/, adapter, evaluator, execution
baselines/<method>/      the method's runner
ours/                    Active Defense runner, frozen contracts and defense
run.py                   the only evaluation entry point
```

`core/adapter.py` is the single abstract adapter interface.  Each benchmark has
one concrete adapter.  Baselines do not define adapters; their `runner.py`
selects how the method consumes a benchmark adapter.

## Frozen protocols

| benchmark | clean | attack | attack utility |
|---|---:|---:|---:|
| AgentDojo | 97 | 629 | 629 |
| SkillInject | 180 | 180 | 180 |
| SCR-CapFlow | 150 | 150 | 150 |
| SCR-AuthBlur | 116 | 116 | 116 |
| SCR-TrustLift | 401 | 401 | 401 |
| MSB | 13 | 622 | 415 |
| MCPTox | 357 | 1348 | 1348 |

The exact files and SHA-256 digests are recorded in each
`benchmarks/<name>/protocol.json`.  A run fails before model calls if a frozen
file drifts.

## Commands

Validate all data and denominators without any model call:

```bash
python3 -m code.run --verify-only
python3 -m code.run --verify-only --verify-results experiment_results
```

Inspect an invocation without executing it:

```bash
python3 -m code.run \
  --benchmark skillinject --method progent \
  --output /tmp/skillinject-progent --workers 8 --dry-run
```

Arguments after `--` are forwarded to the benchmark-native execution module.
The target, defense and judge model roles are explicit top-level options.

AgentDojo attack payloads are selected independently of the method.  For the
local AdapTools-style adaptive payload generator, pass the attack through the
native arguments so every baseline consumes the same frozen pairs:

```bash
ADAPTOOLS_VARIANT=task_bridge \
python3 -m code.run \
  --benchmark agentdojo --method undefended \
  --output experiment_results/AgentDojo/AdapTools/undefended \
  --workers 1 -- --attack adaptools --max-pairs 20
```

`ADAPTOOLS_VARIANT` selects the payload renderer.  `ADAPTOOLS_CACHE` can point to
a JSON object of frozen payloads keyed by suite/task/injection/vector, and
`ADAPTOOLS_LOG` records the rendered injections for audit.

By default, `adaptools` is deterministic and does not call a separate attack
model.  To use GPT 5.4 as the AdapTools payload generator, first materialize a
frozen cache, then replay that cache for every method:

```bash
python3 -m code.benchmarks.agentdojo.adaptive.adaptools_cache \
  --output experiment_results/AgentDojo/AdapTools/cache/gpt54_task_bridge.json \
  --model gpt-5.4-2026-03-05 \
  --variant task_bridge \
  --max-pairs 20 --resume
```

This keeps the model roles explicit: `--model` above is the attack-side payload
generator, while `--target-model` in `code.run` remains the victim agent model.

For repeatable method × variant sweeps, use the AgentDojo AdapTools wrapper. It
only expands to unified `code.run` invocations; it does not introduce a separate
benchmark protocol or denominator:

```bash
python3 -m code.benchmarks.agentdojo.adaptive.adaptools_sweep \
  --output-root experiment_results/AgentDojo/AdapTools/sweep \
  --methods ours,undefended,camel,progent,melon,spotlighting,tool_filter \
  --variants task_bridge,tool_plan,context_note \
  --cache experiment_results/AgentDojo/AdapTools/cache/gpt54_task_bridge.json \
  --generator-model gpt-5.4-2026-03-05 \
  --target-model deepseek-v4-flash \
  --max-pairs 20 --workers 1 --run-workers 1 --resume
```

Use `--dry-run` to inspect the generated commands before model calls.  Each job
writes results under `<output-root>/<method>/<variant>/` and records rendered
payloads in that directory's `injections.jsonl`.

## Active Defense

`ours/defense/` is the preserved current implementation, including the latest
Contract/Binding protocol, PLANT carrier replay, WRAP checks, continuation,
UnitBroker/NestedEffect mediation and identity-preserving placement work.
Frozen reviewed Contracts live under `ours/contracts/<benchmark>/`; trusted
method manifests live under `ours/manifests/` and reference benchmark data
rather than duplicating it.

Adaptive-attack generators and replay helpers are benchmark artifacts, not
core defense logic.  They live under `benchmarks/<name>/adaptive/`; benchmark
execution modules live under `benchmarks/<name>/execution/`; shared MCP replay
runtime lives under `benchmarks/mcp_common/`.
