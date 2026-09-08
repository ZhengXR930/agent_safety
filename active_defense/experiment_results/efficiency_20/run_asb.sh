#!/usr/bin/env bash
# Efficiency harness: ASB-OPI, 20 fixed attack ids, all baselines + Ours.
# Each method runs in its own process so USAGE token accounting is isolated.
set -uo pipefail
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
PY=/usr/bin/python3.11
ROOT=experiment_results/efficiency_20/DeepSeek/ASB-OPI
mkdir -p "$ROOT"

IDS=$($PY -c "import json;print(' '.join('--case-id '+i for i in json.load(open('experiment_results/efficiency_20/DeepSeek/sample_ids.json'))['ASB-OPI']))")

FROZEN=experiment_results/ASB-OPI/Ours/DeepSeek/contracts

for M in undefended ours progent camel drift melon spotlighting tool_filter agentshield taskshield; do
  OUT="$ROOT/$M"
  mkdir -p "$OUT"
  EXTRA=""
  if [ "$M" = "ours" ]; then EXTRA="--contract-cache-root $FROZEN"; fi
  echo "===== ASB-OPI $M ====="
  USAGE_DUMP_PATH="$OUT/usage.json" \
  $PY -m code.benchmarks.asb_opi.execution.glue \
    --method "$M" --model deepseek-v4-flash --defense-model deepseek-v4-flash \
    --split attack --workers 8 --output "$OUT" $EXTRA $IDS \
    > "$OUT/run.log" 2>&1
  echo "exit=$? usage=$(cat "$OUT/usage.json" 2>/dev/null | tr -d '\n' | head -c 300)"
done
echo "ASB-OPI efficiency DONE"
