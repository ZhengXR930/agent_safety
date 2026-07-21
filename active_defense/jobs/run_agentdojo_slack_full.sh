#!/usr/bin/env bash
set -u

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense"
OUT="${AD_OUT:?set AD_OUT to a fresh result directory}"
PAIRS="$ROOT/results/agentdojo_hybrid_compact_full_20260719/slack_pairs.json"
PLAN="$OUT/defense_plan"

cd "$ROOT" || exit 1
mkdir -p "$OUT/logs"

attempt=1
while [ "$attempt" -le 3 ]; do
  python -u code/run_agentdojo.py \
    --suite slack \
    --all-compatible-pairs \
    --pair-manifest "$PAIRS" \
    --seed 20260720 \
    --attack important_instructions \
    --agent-model deepseek-chat \
    --contract-model gpt-5.5-2026-04-24 \
    --plant-model deepseek-chat \
    --plant-review-model gpt-5.5-2026-04-24 \
    --boundary-mode declared \
    --plan-store "$PLAN" \
    --output "$OUT/slack.json" \
    --resume && exit 0
  attempt=$((attempt + 1))
  sleep 30
done
exit 1
