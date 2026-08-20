# ASB-OPI full protocol

This benchmark slice uses the official ASB OPI setting (`observation_prompt_injection`, `context_ignoring`, `attack_tool=all`) over all official ASB tasks.

Denominators: BU uses 51 clean tasks from the 10 ASB agents; AU/ASR use 2040 attack pairs, pairing each task with each same-agent official attacker tool.

All reported methods consume `protocol.json` through `execution/glue.py`. The runner preserves ASB planning/action/observation-injection structure and ASB native string scorer.

For `ours`, TaskContractor synthesizes a Contract from the trusted user query and trusted normal-tool manifest. The OPI attacker tool is runtime-visible but not an operator-trusted manifest capability; if called, it is mediated as an unknown effect.
