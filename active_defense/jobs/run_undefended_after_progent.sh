#!/usr/bin/env bash
set -u

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense"
cd "$ROOT" || exit 1
while pgrep -f '^bash jobs/run_progent_direct_all_suites.sh$' >/dev/null; do
  sleep 30
done
exec bash jobs/run_undefended_direct_all_suites.sh
