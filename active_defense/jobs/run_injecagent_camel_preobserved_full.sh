#!/usr/bin/env bash
set -euo pipefail

cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense

export CAMEL_INTERPRETER_TIMEOUT=60

python code/run_injecagent_camel_original.py \
  --data-dir ../benchmarks/InjecAgent/data \
  --policy code/baselines/camel/policies/injecagent_policy_v1.json \
  --output experiment_stage/injecagent_camel_preobserved_enhanced_full_20260722.json \
  --attack both \
  --setting enhanced \
  --model deepseek-chat \
  --protocol preobserved \
  --resume

python code/evaluate_injecagent_utility.py \
  --data-dir ../benchmarks/InjecAgent/data \
  --assets code/baselines/camel/policies/injecagent_utility_assets_v1.json \
  --results experiment_stage/injecagent_camel_preobserved_enhanced_full_20260722.json \
  --output experiment_stage/injecagent_camel_preobserved_enhanced_full_utility_20260722.json \
  --judge-model deepseek-chat \
  --resume
