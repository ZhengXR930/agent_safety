# Invocation surface

Five datasets across three agent units. Every dataset has exactly two entries:
one for the active defense, one for its controls. Entries select an
implementation and forward all remaining flags unchanged, so each harness keeps
its own CLI (`--help` on an entry shows the switch; `--help` after the switch
shows the implementation's own flags).

| unit | dataset | active defense | controls |
|---|---|---|---|
| tool | AgentDojo | `run_agentdojo.py [--mode smoke\|full]` | `run_agentdojo_baselines.py --defense undefended\|melon\|native\|matrix` |
| MCP | MCPTox | `run_mcptox.py` | `run_mcptox_baselines.py --defense mcpguard\|mcpguard-probe\|pipelock` |
| MCP | MSB | `run_msb.py` | `run_msb_baselines.py --defense clean-fp\|score` |
| skill | SCRBench | `run_scr.py --suite capflow\|authblur\|generic` | `run_scr_baselines.py --defense baselines\|clawguard\|guardian` |
| skill | SkillInject | `run_skillinject.py --sandbox <dir> --task <text>` | `run_skillinject_baselines.py --defense guards` |

Run from the repository root; the entries put it on `sys.path` themselves:

```bash
python code/run_agentdojo.py --suite banking --n 4
python code/run_scr.py --suite capflow --scr-root <path> --case <id>
python code/run_agentdojo_baselines.py --defense melon --suite banking
```

## Layout

```
code/
  run_<dataset>*.py     the invocation surface (this table) — nothing else at top level
  defense/              the method: state, contract, binding/proof, wrap, plant,
                        continuation, engine, and tests
  benchmarks/           one adapter per unit — the defense seam
  harness/              implementations behind the entries
  tools/                data preparation and probes
  pilots/               development pilots (e.g. the three PLANT carriers)
```

## Adapter seam

An adapter needs only four verbs, identical for tool, MCP and skill units:

| verb | purpose |
|---|---|
| `episode.observe(cap, args, value)` | a Contract-bound read; returns the instrumented view |
| `episode.expose(source, value)` | untrusted input that is not an acquisition (skill narrative, MCP resource) |
| `episode.arm_substrate(surface, sample)` | returns a token the adapter embeds in a native artifact |
| `episode.commit(channel, actor, payload, proof_refs=…)` | report a boundary: `call`, `response`, `state`, `artifact` |
| `episode.continue_decision(decision)` | consume one repair/replan/abort plan; ignored plans remain fail-closed |

A `replan` result is a suspension boundary, not a tool error. The adapter must
discard the current Agent session and start one fresh session from
`decision.continuation["state"]`. AgentDojo, SCR and SkillInject implement this
boundary directly; the controller itself makes no model call.

One MCPTox control is a Node runner and is invoked directly, not through an
entry: `node code/harness/run_defender_mcptox_full.mjs`.

## Known gaps

- **A PLANT marker rewrites the handle it instruments**, so a benchmark's
  literal attack-token oracle stops matching what the agent actually typed. The
  SkillInject adapter therefore reports `attack_effect` (literal oracle),
  `plant_commitments` and `attack_attempted` separately; use the commitment as
  the attack signal whenever a marker is deployed.
- **MCPTox and MSB share one active-defense implementation**
  (`harness/mcp_ours.py`) that evaluates the paired sample in a single pass, so
  `run_mcptox.py` and `run_msb.py` currently drive the same evaluation.
