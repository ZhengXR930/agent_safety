#!/usr/bin/env bash
set -euo pipefail

cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense

output_dir="experiment_stage/asb_camel_pilot20_20260723"
mkdir -p "$output_dir"

for condition in clean opi; do
  for agent_index in $(seq 0 9); do
    output="$output_dir/${condition}_agent_${agent_index}.json"
    log="$output_dir/${condition}_agent_${agent_index}.log"
    if [[ -s "$output" ]]; then
      echo "skip $condition agent=$agent_index"
      continue
    fi
    echo "run $condition agent=$agent_index"
    python -u code/run_asb_camel_sanity.py \
      --condition "$condition" \
      --agent-index "$agent_index" \
      --output "$output" 2>&1 | tee "$log"
  done
done
