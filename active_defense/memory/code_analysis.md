# Code Analysis

## Target

- Method: perception-guided PLANT–WRAP active defense
- Primary metrics: AgentDojo ASR and executed malicious effects
- Secondary metrics: benign/attack utility, benign Auditor/Approval rate, runtime cost
- Evidence boundary: task probes are smoke/proxy; promotion requires a frozen full benchmark run

## Hard Constraints

- No benchmark-specific strings, tool allowlists, or GT-derived authorization.
- No Agent internal reasoning, execution order, or invented derivation receipts.
- One trusted task produces one frozen Contract reused by benign and attack runs.
- Runtime content cannot create write authority; PLANT and WRAP remain independent signals.

## Hot Paths

| Path | Role |
| --- | --- |
| `code/defense/taskcontractor.py` | trusted task to independent authorization clauses |
| `code/defense/wrap.py` | observation/effect boundary gate |
| `code/defense/plant.py` | active intervention and commitment signal |
| `code/benchmarks/agentdojo.py` | observable runtime and evaluation adapter |

## Exhausted Families

- Ordered instruction programs and internal derivation receipts: unobservable and utility-damaging.
- Free-text `relation` plus SemanticBinder authorization: unstable implicit policy and prompt-injection surface.
- Per-instruction Agent turns: turns Contract into execution IR and multiplies latency.

## Current LEAP

Replace ordered instructions with independent `action/sources/arguments` clauses. Arguments use only
`literal`, `source`, or `content`; runtime provenance contains only observable tool boundaries.
