#!/usr/bin/env bash
set -u
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
log_dir="experiment_results/ASB-OPI/_logs"
status="$log_dir/full_alltasks_status.tsv"
pids="$log_dir/full_alltasks_pids.tsv"
: > "$status"
: > "$pids"
run_method() {
  local method="$1" label="$2" workers="$3"
  local out="experiment_results/ASB-OPI/${label}/DeepSeek"
  local log="$log_dir/${method}_deepseek_full_alltasks.log"
  echo -e "START\t${method}\t$(date '+%F %T')" >> "$status"
  python3 code/run.py --benchmark asb_opi --method "$method" \
    --target-model deepseek-v4-flash --defense-model deepseek-v4-flash \
    --output "$out" --workers "$workers" --resume \
    > "$log" 2>&1
  local rc=$?
  echo -e "END\t${method}\t${rc}\t$(date '+%F %T')" >> "$status"
  return "$rc"
}
launch() {
  local method="$1" label="$2" workers="$3"
  while [ "$(jobs -rp | wc -l)" -ge 3 ]; do
    wait -n || true
  done
  run_method "$method" "$label" "$workers" &
  echo -e "${method}\t$!\t${workers}\t${label}" >> "$pids"
}
launch undefended Undefended 4
launch ours Ours 4
launch camel CaMeL 4
launch drift DRIFT 2
launch melon MELON 4
launch spotlighting Spotlighting 4
launch tool_filter ToolFilter 4
launch progent Progent 1
rc=0
for pid in $(jobs -rp); do
  wait "$pid" || rc=1
done
exit "$rc"
