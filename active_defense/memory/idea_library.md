# Idea Library

## Hard Constraints

- Fixed AgentDojo evaluator and data.
- No GT except a future user-approval simulator.
- No internal reasoning extraction or benchmark-specific rules.

## Active Backlog

| ID | Type | Hypothesis | Evidence | Status |
| --- | --- | --- | --- | --- |
| L01 | LEAP | Independent minimal clauses eliminate Contractor ambiguity and instruction-chain failures | task1/task11 plus real attack-attempt probes | active |

## Rejected / Exhausted

| Family | Reason |
| --- | --- |
| ordered instruction receipts | requires observing internal computation |
| SemanticBinder as gate | becomes an implicit natural-language policy |
| substring/token provenance | benchmark-sensitive and unsound |

## Promotion Gate

No promotion from smoke probes. Require frozen full benchmark ASR, executed-effect ASR, utility and benign
Auditor/Approval rates, with the same Contract shared across paired runs.
