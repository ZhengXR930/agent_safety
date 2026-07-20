#!/usr/bin/env bash
set -u

root="results/agentdojo_full_deepseek_v4_gpt55review_20260719"
pids=()

for suite in banking slack travel workspace; do
  python -u code/run_agentdojo.py \
    --suite "$suite" --random-pairs 999 --resume --seed 20260718 \
    --attack direct --agent-model deepseek-chat --contract-model deepseek-chat \
    --plant-model deepseek-chat --plant-review-model gpt-5.5-2026-04-24 \
    --boundary-mode declared --plan-store "$root/defense_plan" \
    --output "$root/$suite.json" >"$root/$suite.log" 2>&1 &
  pids+=("$!")
done

status=0
for pid in "${pids[@]}"; do
  wait "$pid" || status=1
done
exit "$status"
