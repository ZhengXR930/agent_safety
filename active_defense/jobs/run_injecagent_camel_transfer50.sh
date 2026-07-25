#!/usr/bin/env bash
set -u
ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense"
DATA="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/benchmarks/InjecAgent/data"
OUT="$ROOT/experiment_stage/injecagent_camel_transfer50_20260722"
INDICES="0,20,40,60,80,100,120,140,160,180,200,220,240,260,280,300,320,340,360,380,400,420,440,460,480"
mkdir -p "$OUT"
cd "$ROOT" || exit 1
python -u code/run_injecagent_camel_transfer.py --data-dir "$DATA" --attack both \
  --setting enhanced --indices "$INDICES" --model deepseek-chat --mode undefended \
  --output "$OUT/undefended.json" --resume 2>&1 | tee "$OUT/undefended.log" || exit 1
python -u code/run_injecagent_camel_transfer.py --data-dir "$DATA" --attack both \
  --setting enhanced --indices "$INDICES" --model deepseek-chat --mode camel \
  --output "$OUT/camel.json" --resume 2>&1 | tee "$OUT/camel.log"
