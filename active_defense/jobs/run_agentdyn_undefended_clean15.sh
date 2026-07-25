#!/usr/bin/env bash
set -euo pipefail

cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense

output_dir="experiment_stage/agentdyn_undefended_clean15_20260723"
mkdir -p "$output_dir"

PYTHONPATH="baseline/AutoDojo/agentdojo/src${PYTHONPATH:+:$PYTHONPATH}" \
python -u code/run_agentdyn_undefended_clean_pilot.py \
  --output-dir "$output_dir" \
  2>&1 | tee -a "$output_dir/run.log"
