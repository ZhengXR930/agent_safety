#!/usr/bin/env bash
set -euo pipefail

out_dir="experiment_stage/tap_camel_slack_stratified_20260722"
mkdir -p "$out_dir"

pairs=(
  "injection_dora_0:user_task_2:injection_task_1"
  "injection_web_0:user_task_0:injection_task_1"
  "prompt_injection_channel:user_task_5:injection_task_1"
  "prompt_injection_eve_blog:user_task_4:injection_task_1"
  "prompt_injection_restaurant:user_task_6:injection_task_1"
)

for spec in "${pairs[@]}"; do
  IFS=: read -r vector user_task injection_task <<< "$spec"
  python -u -m code.run_tap_ours \
    --defense camel \
    --suite slack \
    --user-task "$user_task" \
    --injection-task "$injection_task" \
    --roots 1 \
    --branching-factor 2 \
    --width 2 \
    --depth 2 \
    --seed 20260722 \
    --attacker-model deepseek-chat \
    --judge-model deepseek-chat \
    --agent-model deepseek-chat \
    --output "$out_dir/${vector}.json"
done
