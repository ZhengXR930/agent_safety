#!/usr/bin/env bash
set -u

root="results/agentdojo_slack_full_matrix_20260719"
common=(--suite slack --all-compatible-pairs --pair-manifest "$root/slack_pairs.json"
        --resume --attack direct --agent-model deepseek-chat --plant-model deepseek-chat
        --boundary-mode declared)

python -u code/run_agentdojo.py "${common[@]}" \
  --contract-model deepseek-chat --plant-review-model deepseek-chat \
  --plan-store "$root/deepseek_plan" --output "$root/all_deepseek.json" \
  >"$root/all_deepseek.log" 2>&1 &
deepseek_pid=$!

python -u code/run_agentdojo.py "${common[@]}" \
  --contract-model gpt-5.5-2026-04-24 --plant-review-model gpt-5.5-2026-04-24 \
  --plan-store "$root/hybrid_plan" --output "$root/hybrid_gpt55_defense.json" \
  >"$root/hybrid_gpt55_defense.log" 2>&1 &
hybrid_pid=$!

status=0
wait "$deepseek_pid" || status=1
wait "$hybrid_pid" || status=1
exit "$status"
