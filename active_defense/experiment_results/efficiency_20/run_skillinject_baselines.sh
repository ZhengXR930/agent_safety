#!/bin/bash
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/SkillInject
DRIVER="$ROOT/driver_baselines.log"; : > "$DRIVER"
PAIRS="--pair id001_task3 --pair id003_task0 --pair id003_task3 --pair id006_task0 --pair id006_task4 --pair id007_task0 --pair id008_task4 --pair id011_task0 --pair id014_task2 --pair id016_task0 --pair id018_task1 --pair id018_task3 --pair id022_task0 --pair id026_task1 --pair id028_task3 --pair id032_task4 --pair id033_task0 --pair id033_task1 --pair id033_task3 --pair id037_task3"
for B in undefended clawguard progent taskshield dynamic_guardian; do
  OUT="$ROOT/$B"; rm -rf "$OUT"; mkdir -p "$OUT/usage"
  echo "===== SkillInject $B =====" | tee -a "$DRIVER"
  USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
  /usr/bin/python3.11 -m code.benchmarks.skillinject.execution.baseline_batch \
    --output-root "$OUT" --work-root "$OUT/work" --workers 8 \
    --baseline "$B" --model deepseek-v4-flash --guard-model deepseek-v4-flash \
    $PAIRS >> "$OUT/run.log" 2>&1
  echo "$B exit=$?" | tee -a "$DRIVER"
done
echo "ALL DONE" | tee -a "$DRIVER"
