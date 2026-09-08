#!/bin/bash
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/AgentDojo
MANIFEST=experiment_results/efficiency_20/DeepSeek/AgentDojo_banking20_pairs.json
CONTRACT=code/ours/contracts/agentdojo/banking.json
DRIVER="$ROOT/DRIVER.log"; mkdir -p "$ROOT"; : > "$DRIVER"
PY=/usr/bin/python3.11
AM=deepseek-v4-flash

run() {  # name  module  extra-args...
  local name="$1"; shift; local mod="$1"; shift
  local OUT="$ROOT/$name"; mkdir -p "$OUT/usage"
  echo "===== AgentDojo $name =====" | tee -a "$DRIVER"
  USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
  $PY -m "$mod" --suite banking --pair-manifest "$MANIFEST" \
    --output "$OUT/banking.json" --agent-model "$AM" \
    --attack important_instructions "$@" >> "$OUT/run.log" 2>&1
  echo "$name exit=$?" | tee -a "$DRIVER"
}

run ours       code.benchmarks.agentdojo.execution.ours       --contract-file "$CONTRACT" --ablation-mode full --contract-model "$AM" --frozen-contracts-only
run undefended code.benchmarks.agentdojo.execution.undefended
run melon      code.benchmarks.agentdojo.execution.melon
run agentshield code.benchmarks.agentdojo.execution.agentshield
run taskshield code.benchmarks.agentdojo.execution.taskshield --guard-model "$AM"
run drift      code.benchmarks.agentdojo.execution.native --defense drift
run camel      code.benchmarks.agentdojo.execution.native --defense camel
run progent    code.benchmarks.agentdojo.execution.native --defense progent --policy-model "$AM"
run spotlighting code.benchmarks.agentdojo.execution.native --defense spotlighting
run tool_filter  code.benchmarks.agentdojo.execution.native --defense tool_filter
echo "ALL DONE" | tee -a "$DRIVER"
