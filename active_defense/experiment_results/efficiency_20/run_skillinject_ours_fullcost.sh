#!/bin/bash
# SkillInject full-cost: live contract generation (NOT frozen) so TaskContractor
# token cost is counted, matching ASB/MCPTox ours_fullcost accounting.
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/SkillInject
OUT="$ROOT/ours_fullcost"; mkdir -p "$OUT/usage"
PAIRS="--pair id001_task3 --pair id003_task0 --pair id003_task3 --pair id006_task0 --pair id006_task4 --pair id007_task0 --pair id008_task4 --pair id011_task0 --pair id014_task2 --pair id016_task0 --pair id018_task1 --pair id018_task3 --pair id022_task0 --pair id026_task1 --pair id028_task3 --pair id032_task4 --pair id033_task0 --pair id033_task1 --pair id033_task3 --pair id037_task3"
echo "===== SkillInject ours_fullcost (live contract-gen) ====="
USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
/usr/bin/python3.11 -m code.benchmarks.skillinject.execution.batch \
  --output-root "$OUT" --work-root "$OUT/work" --workers 4 \
  --model deepseek-v4-flash --defense-model deepseek-v4-flash \
  --ablation-mode full --case-timeout 1800 \
  $PAIRS >> "$OUT/run.log" 2>&1
echo "fullcost exit=$?"
