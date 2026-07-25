#!/usr/bin/env bash
set -euo pipefail

cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense

condition="${1:?usage: $0 <undefended|camel>}"
case "$condition" in
  undefended)
    output_dir="experiment_stage/agentdyn_undefended_clean_full_20260723"
    runner="code/run_agentdyn_undefended_clean_pilot.py"
    ;;
  camel)
    output_dir="experiment_stage/agentdyn_camel_clean_full_20260723"
    runner="code/run_agentdyn_camel_clean_pilot.py"
    ;;
  *)
    echo "unknown condition: $condition" >&2
    exit 2
    ;;
esac

mkdir -p "$output_dir"
PYTHONPATH="baseline/AutoDojo/agentdojo/src${PYTHONPATH:+:$PYTHONPATH}" \
python -u "$runner" --full --output-dir "$output_dir" \
  2>&1 | tee -a "$output_dir/run.log"
