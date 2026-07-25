#!/usr/bin/env bash
set -u

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense"
OUT="$ROOT/experiment_stage/progent_remaining_20260722"
mkdir -p "$OUT/logs"
cd "$ROOT" || exit 1

run_job() {
  local id="$1"
  shift
  echo "[$(date -Iseconds)] START $id" | tee -a "$OUT/queue.log"
  if "$@" 2>&1 | tee "$OUT/logs/$id.log"; then
    echo "[$(date -Iseconds)] COMPLETE $id" | tee -a "$OUT/queue.log"
  else
    echo "[$(date -Iseconds)] FAILED $id" | tee -a "$OUT/queue.log"
    return 1
  fi
}

run_job banking_clean python -u code/run_progent_clean_suite.py \
  --suite banking --output "$OUT/banking_clean.json" --resume
run_job banking_attack python -u code/run_progent_attack_suite.py \
  --suite banking --attack important_instructions \
  --output "$OUT/banking_attack.json" --resume

run_job travel_clean python -u code/run_progent_clean_suite.py \
  --suite travel --output "$OUT/travel_clean.json" --resume
run_job travel_attack python -u code/run_progent_attack_suite.py \
  --suite travel --attack important_instructions \
  --injection-tasks injection_task_0,injection_task_1,injection_task_2,injection_task_3,injection_task_4 \
  --output "$OUT/travel_attack.json" --resume

# The public AutoDojo cache has no GPT-4o-authored Workspace policy file.
# Build and reuse a clearly labelled DeepSeek-authored cache for this suite.
run_job workspace_clean python -u code/run_progent_clean_suite.py \
  --suite workspace --policy-model deepseek-chat --progent-cache-label deepseek-chat \
  --output "$OUT/workspace_clean.json" --resume
run_job workspace_attack python -u code/run_progent_attack_suite.py \
  --suite workspace --attack important_instructions \
  --policy-model deepseek-chat --progent-cache-label deepseek-chat \
  --injection-tasks injection_task_0,injection_task_1,injection_task_2,injection_task_3,injection_task_4,injection_task_5 \
  --output "$OUT/workspace_attack.json" --resume

echo "[$(date -Iseconds)] ALL_COMPLETE" | tee -a "$OUT/queue.log"
