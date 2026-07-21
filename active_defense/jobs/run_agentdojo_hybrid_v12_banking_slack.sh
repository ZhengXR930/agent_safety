#!/usr/bin/env bash
set -u

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense"
OUT="$ROOT/results/agentdojo_hybrid_v12_full_20260721"
PLAN="$OUT/defense_plan"
PAIRS="$ROOT/results/agentdojo_hybrid_compact_full_20260719"
cd "$ROOT" || exit 1

run_suite() {
  suite="$1"
  attempt=1
  while [ "$attempt" -le 3 ]; do
    python -u code/run_agentdojo.py \
      --suite "$suite" \
      --all-compatible-pairs \
      --pair-manifest "$PAIRS/${suite}_pairs.json" \
      --seed 20260720 \
      --attack important_instructions \
      --agent-model deepseek-chat \
      --contract-model gpt-5.5-2026-04-24 \
      --plant-model deepseek-chat \
      --plant-review-model gpt-5.5-2026-04-24 \
      --boundary-mode declared \
      --plan-store "$PLAN" \
      --output "$OUT/${suite}.json" \
      --resume && return 0
    attempt=$((attempt + 1))
    sleep 30
  done
  return 1
}

run_suite banking || exit 1
run_suite slack || exit 1
