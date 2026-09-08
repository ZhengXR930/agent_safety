#!/bin/bash
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/SkillInject
OUT="$ROOT/ours"; mkdir -p "$OUT/usage"
echo "===== SkillInject ours retry2 (id014_task2, id037_task3, 1800s, workers2) ====="
USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
/usr/bin/python3.11 -m code.benchmarks.skillinject.execution.batch \
  --output-root "$OUT" --work-root "$OUT/work" --workers 2 \
  --model deepseek-v4-flash --defense-model deepseek-v4-flash \
  --ablation-mode full --frozen-contracts-only --case-timeout 1800 \
  --pair id014_task2 --pair id037_task3 >> "$OUT/run_retry2.log" 2>&1
echo "retry2 exit=$?"
