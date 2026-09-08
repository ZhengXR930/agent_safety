#!/bin/bash
# Lightweight 20-pair SkillInject efficiency subset (one per case, no scripts,
# minimal files, runaway cases excluded). Same 20 pairs for APEX + baselines;
# cache-aware tracker. Frozen contracts for APEX so contract-gen cancels out.
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/SkillInject_light20
PAIRS="--pair id020_task0 --pair id026_task0 --pair id028_task0 --pair id030_task0 --pair id032_task0 --pair id022_task0 --pair id023_task0 --pair id021_task0 --pair id027_task0 --pair id033_task1 --pair id035_task0 --pair id037_task0 --pair id006_task0 --pair id036_task0 --pair id034_task0 --pair id008_task0 --pair id029_task0 --pair id038_task0 --pair id017_task0 --pair id018_task0"

# --- APEX (full defense, frozen contracts) ---
OUT="$ROOT/ours"; rm -rf "$OUT"; mkdir -p "$OUT/usage"
echo "===== light20 APEX ====="
USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
/usr/bin/python3.11 -m code.benchmarks.skillinject.execution.batch \
  --output-root "$OUT" --work-root "$OUT/work" --workers 8 \
  --model deepseek-v4-flash --defense-model deepseek-v4-flash \
  --ablation-mode full --case-timeout 1800 --frozen-contracts-only \
  $PAIRS >> "$OUT/run.log" 2>&1
echo "APEX exit=$?"

# --- baselines ---
for B in undefended clawguard taskshield dynamic_guardian; do
  OUT="$ROOT/$B"; rm -rf "$OUT"; mkdir -p "$OUT/usage"
  echo "===== light20 $B ====="
  USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
  /usr/bin/python3.11 -m code.benchmarks.skillinject.execution.baseline_batch \
    --output-root "$OUT" --work-root "$OUT/work" --workers 8 \
    --baseline "$B" --model deepseek-v4-flash --guard-model deepseek-v4-flash \
    $PAIRS >> "$OUT/run.log" 2>&1
  echo "$B exit=$?"
done
echo "LIGHT20 ALL DONE"
