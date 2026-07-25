#!/usr/bin/env bash
set -u

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense"
OUT="$ROOT/experiment_stage/undefended_direct_all_20260722"
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

run_job banking_undefended python -u code/run_progent_attack_suite.py \
  --suite banking --attack direct --evaluation-pipeline undefended \
  --output "$OUT/banking_undefended.json" --resume
run_job slack_undefended python -u code/run_progent_attack_suite.py \
  --suite slack --attack direct --evaluation-pipeline undefended \
  --output "$OUT/slack_undefended.json" --resume
run_job travel_undefended python -u code/run_progent_attack_suite.py \
  --suite travel --attack direct --evaluation-pipeline undefended \
  --injection-tasks injection_task_0,injection_task_1,injection_task_2,injection_task_3,injection_task_4 \
  --output "$OUT/travel_undefended.json" --resume
run_job workspace_undefended python -u code/run_progent_attack_suite.py \
  --suite workspace --attack direct --evaluation-pipeline undefended \
  --policy-model deepseek-chat --progent-cache-label deepseek-chat \
  --injection-tasks injection_task_0,injection_task_1,injection_task_2,injection_task_3,injection_task_4,injection_task_5 \
  --output "$OUT/workspace_undefended.json" --resume

echo "[$(date -Iseconds)] ALL_COMPLETE" | tee -a "$OUT/queue.log"
