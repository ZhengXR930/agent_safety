#!/bin/bash
# Single-sample probe: observation-reuse in recovery envelope (id033_task0).
# Uses frozen contract (contract-gen cancels out) so the delta isolates replan cost.
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/SkillInject
MODE="${1:-reuse}"   # reuse | noreuse
OUT="$ROOT/ours_${MODE}_probe"; rm -rf "$OUT"; mkdir -p "$OUT/usage"
EXTRA=""
if [ "$MODE" = "noreuse" ]; then export APEX_DISABLE_OBS_REUSE=1; fi
echo "===== SkillInject probe id033_task0 mode=$MODE ====="
USAGE_DUMP_PATH="$OUT/usage/u_{pid}.json" \
/usr/bin/python3.11 -m code.benchmarks.skillinject.execution.batch \
  --output-root "$OUT" --work-root "$OUT/work" --workers 1 \
  --model deepseek-v4-flash --defense-model deepseek-v4-flash \
  --ablation-mode full --case-timeout 1800 \
  --frozen-contracts-only \
  --pair id033_task0 >> "$OUT/run.log" 2>&1
echo "probe mode=$MODE exit=$?"
