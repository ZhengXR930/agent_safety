#!/usr/bin/env bash
set -u

cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense

QUEUE_DIR="experiment_stage/queue/20260723_injecagent_full"
STATE_HELPER="/home/tiger/.codex/skills/experiment/scripts/experiment_queue_state.py"
DATA_DIR="../benchmarks/InjecAgent/data"
ASSETS="code/baselines/camel/policies/injecagent_utility_assets_v1.json"
CAMEL_POLICY="code/baselines/camel/policies/injecagent_policy_v1.json"

run_job() {
  local job_id="$1"
  local output="$2"
  shift 2
  python "$STATE_HELPER" set-status --queue-dir "$QUEUE_DIR" \
    --job-id "$job_id" --status running --inc-attempt
  "$@"
  local status=$?
  if [[ $status -eq 0 && -s "$output" ]]; then
    python "$STATE_HELPER" set-status --queue-dir "$QUEUE_DIR" \
      --job-id "$job_id" --status completed --output "$output"
  else
    python "$STATE_HELPER" set-status --queue-dir "$QUEUE_DIR" \
      --job-id "$job_id" --status failed_other \
      --error "exit=$status output=$output"
    exit "$status"
  fi
}

run_job undefended_dh \
  experiment_stage/injecagent_full_undefended_dh_20260723.json \
  python -u code/run_injecagent_standard.py \
    --data-dir "$DATA_DIR" \
    --output experiment_stage/injecagent_full_undefended_dh_20260723.json \
    --defense undefended --attack dh --setting enhanced \
    --model deepseek-chat --resume

run_job undefended_ds \
  experiment_stage/injecagent_full_undefended_ds_20260723.json \
  python -u code/run_injecagent_standard.py \
    --data-dir "$DATA_DIR" \
    --output experiment_stage/injecagent_full_undefended_ds_20260723.json \
    --defense undefended --attack ds --setting enhanced \
    --model deepseek-chat --resume

run_job camel_dh \
  experiment_stage/injecagent_full_camel_dh_20260723.json \
  python -u code/run_injecagent_camel_original.py \
    --data-dir "$DATA_DIR" --policy "$CAMEL_POLICY" \
    --output experiment_stage/injecagent_full_camel_dh_20260723.json \
    --attack dh --setting enhanced --model deepseek-chat \
    --protocol preobserved --resume

run_job camel_ds \
  experiment_stage/injecagent_full_camel_ds_20260723.json \
  python -u code/run_injecagent_camel_original.py \
    --data-dir "$DATA_DIR" --policy "$CAMEL_POLICY" \
    --output experiment_stage/injecagent_full_camel_ds_20260723.json \
    --attack ds --setting enhanced --model deepseek-chat \
    --protocol preobserved --resume

run_job progent_dh \
  experiment_stage/injecagent_full_progent_dh_20260723.json \
  python -u code/run_injecagent_standard.py \
    --data-dir "$DATA_DIR" \
    --output experiment_stage/injecagent_full_progent_dh_20260723.json \
    --defense progent --attack dh --setting enhanced \
    --model deepseek-chat --policy-model deepseek-chat --resume

run_job progent_ds \
  experiment_stage/injecagent_full_progent_ds_20260723.json \
  python -u code/run_injecagent_standard.py \
    --data-dir "$DATA_DIR" \
    --output experiment_stage/injecagent_full_progent_ds_20260723.json \
    --defense progent --attack ds --setting enhanced \
    --model deepseek-chat --policy-model deepseek-chat --resume

run_job utility_undefended \
  experiment_stage/injecagent_full_undefended_utility_20260723.json \
  python -u code/evaluate_injecagent_utility.py \
    --data-dir "$DATA_DIR" --assets "$ASSETS" \
    --results experiment_stage/injecagent_full_undefended_dh_20260723.json \
              experiment_stage/injecagent_full_undefended_ds_20260723.json \
    --output experiment_stage/injecagent_full_undefended_utility_20260723.json \
    --judge-model deepseek-chat --resume

run_job utility_camel \
  experiment_stage/injecagent_full_camel_utility_20260723.json \
  python -u code/evaluate_injecagent_utility.py \
    --data-dir "$DATA_DIR" --assets "$ASSETS" \
    --results experiment_stage/injecagent_full_camel_dh_20260723.json \
              experiment_stage/injecagent_full_camel_ds_20260723.json \
    --output experiment_stage/injecagent_full_camel_utility_20260723.json \
    --judge-model deepseek-chat --resume

run_job utility_progent \
  experiment_stage/injecagent_full_progent_utility_20260723.json \
  python -u code/evaluate_injecagent_utility.py \
    --data-dir "$DATA_DIR" --assets "$ASSETS" \
    --results experiment_stage/injecagent_full_progent_dh_20260723.json \
              experiment_stage/injecagent_full_progent_ds_20260723.json \
    --output experiment_stage/injecagent_full_progent_utility_20260723.json \
    --judge-model deepseek-chat --resume

python "$STATE_HELPER" summary --queue-dir "$QUEUE_DIR"
