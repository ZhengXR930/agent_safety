#!/usr/bin/env bash
set -euo pipefail

out_dir="experiment_stage/tap_camel_slack_controls10_20260722"
mkdir -p "$out_dir"

pairs=(
  "dora_u2_i1:user_task_2:injection_task_1"
  "dora_u11_i2:user_task_11:injection_task_2"
  "web_u0_i1:user_task_0:injection_task_1"
  "web_u1_i2:user_task_1:injection_task_2"
  "channel_u5_i1:user_task_5:injection_task_1"
  "channel_u7_i2:user_task_7:injection_task_2"
  "eve_u4_i1:user_task_4:injection_task_1"
  "eve_u16_i2:user_task_16:injection_task_2"
  "restaurant_u6_i1:user_task_6:injection_task_1"
  "restaurant_u15_i2:user_task_15:injection_task_2"
)

for spec in "${pairs[@]}"; do
  IFS=: read -r label user_task injection_task <<< "$spec"
  output="$out_dir/${label}.json"
  if [[ -s "$output" ]]; then
    continue
  fi
  python -u -m code.run_tap_ours \
    --defense camel --suite slack \
    --user-task "$user_task" --injection-task "$injection_task" \
    --roots 1 --branching-factor 2 --width 2 --depth 2 \
    --seed 20260722 \
    --attacker-model deepseek-chat --judge-model deepseek-chat \
    --agent-model deepseek-chat --output "$output"
done
