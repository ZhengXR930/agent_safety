# AgentLAB Task Injection benchmark entry

This entry intentionally does not reuse `code/benchmarks/agentdojo`.

- Source suite: AgentLAB's forked AgentDojo task-injection artifact.
- Attack mode: `long_horizon`.
- Clean denominator: all four AgentDojo-compatible suites, 97 user tasks.
- Attack denominator: frozen pairs with available AgentLAB long-horizon payloads, 418 pairs.
- Result root convention: `experiment_results/AgentLAB-TaskInjection/...`.

The runner needs an AgentLAB Task-Injection checkout. By default it looks at
`/tmp/agentlab_probe_20260911/Task-Injection/agentdojo`; override with
`--agentlab-root` or `AGENTLAB_TASK_INJECTION_ROOT`.

Example:

```bash
python3 -m code.run --benchmark agentlab_task_injection --method undefended   --target-model deepseek-v4-flash --workers 8   --output experiment_results/AgentLAB-TaskInjection/DeepSeek -- --resume
```
