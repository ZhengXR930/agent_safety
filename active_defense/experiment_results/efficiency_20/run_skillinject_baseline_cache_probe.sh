#!/bin/bash
# Baseline cache-hit probe: rerun 2 SkillInject pairs per baseline with the
# cache-aware tracker to measure each defense's DeepSeek prefix-cache hit rate.
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/SkillInject
PAIRS="--pair id033_task3 --pair id037_task3"
for B in undefended clawguard taskshield; do
  OUT="$ROOT/${B}_cache_probe"; rm -rf "$OUT"; mkdir -p "$OUT/usage"
  echo "===== SkillInject $B cache probe ====="
  USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
  /usr/bin/python3.11 -m code.benchmarks.skillinject.execution.baseline_batch \
    --output-root "$OUT" --work-root "$OUT/work" --workers 2 \
    --baseline "$B" --model deepseek-v4-flash --guard-model deepseek-v4-flash \
    $PAIRS >> "$OUT/run.log" 2>&1
  echo "$B exit=$?"
done
echo "PROBE DONE"
