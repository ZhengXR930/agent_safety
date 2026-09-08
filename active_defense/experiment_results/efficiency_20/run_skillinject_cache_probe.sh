#!/bin/bash
# Cache-hit probe: rerun 2 SkillInject pairs with the new cache-aware tracker.
# Frozen contracts so contract-gen cost cancels out; measures real DeepSeek
# prefix-cache hit rate on the deep replan turns.
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/SkillInject
OUT="$ROOT/ours_cache_probe"; rm -rf "$OUT"; mkdir -p "$OUT/usage"
USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
/usr/bin/python3.11 -m code.benchmarks.skillinject.execution.batch \
  --output-root "$OUT" --work-root "$OUT/work" --workers 2 \
  --model deepseek-v4-flash --defense-model deepseek-v4-flash \
  --ablation-mode full --case-timeout 1800 \
  --frozen-contracts-only \
  --pair id033_task3 --pair id037_task3 >> "$OUT/run.log" 2>&1
echo "cache probe exit=$?"
