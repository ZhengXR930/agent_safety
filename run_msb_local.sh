#!/bin/zsh
set -euo pipefail

project_root="/Users/zhengxinran/Documents/S2LAB/project/agent_safety"
run_root="$project_root/active_defense"
python_bin="/opt/anaconda3/envs/msb-active-defense/bin/python"
output="$run_root/experiment_results/MSB/Ours/DeepSeek/msb_attack_rerun.json"
workers="${MSB_WORKERS:-4}"

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  read -rs "DEEPSEEK_API_KEY?DeepSeek API key: "
  echo
  export DEEPSEEK_API_KEY
fi

export PYTHONNOUSERSITE=1
export MCP_USE_ANONYMIZED_TELEMETRY=false
cd "$run_root"

outer_resume=()
inner_resume=()
if [[ -f "$output" ]]; then
  outer_resume=(--resume)
  inner_resume=(--resume)
fi

exec "$python_bin" -m code.run \
  --benchmark msb --method ours \
  --target-model deepseek-v4-flash \
  --defense-model deepseek-v4-flash \
  --output "$output" \
  --workers "$workers" "${outer_resume[@]}" -- \
  --mode attack --frozen-contracts-only "${inner_resume[@]}"
