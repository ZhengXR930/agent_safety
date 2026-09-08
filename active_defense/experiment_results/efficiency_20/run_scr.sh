#!/bin/bash
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
ROOT=experiment_results/efficiency_20/DeepSeek/SCR
DRIVER="$ROOT/DRIVER.log"; mkdir -p "$ROOT"; : > "$DRIVER"
PY=/usr/bin/python3.11
AM=deepseek-v4-flash
SCRROOT=/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/benchmarks/SCR_Bench
MANIFEST=experiment_results/SCR/Ours/manifest/capflow.json
FUSION=code/benchmarks/scr/data/scr_fusion/gpt54_official_composition_all
NUMS="4 11 14 21 26 30 31 41 45 53 60 63 68 79 81 98 99 109 120 133"

# Ours: per-case capflow.py, only A+B_neutral condition
OUT="$ROOT/ours"; mkdir -p "$OUT/usage" "$OUT/cases"
echo "===== SCR ours =====" | tee -a "$DRIVER"
for n in $NUMS; do
  cid=$(printf "case%03d" "$n")
  USAGE_DUMP_PATH="$OUT/usage/${cid}_{pid}.json" \
  $PY -m code.benchmarks.scr.execution.capflow \
    --scr-root "$SCRROOT" --manifest-file "$MANIFEST" \
    --case "$n" --condition "A+B_neutral" \
    --target-model "$AM" --defense-model "$AM" --ablation-mode full \
    --contract-file "code/ours/contracts/scr/capflow/${cid}.json" \
    --fusion-dataset "$FUSION" \
    --output "$OUT/cases/${cid}.json" >> "$OUT/run.log" 2>&1
done
echo "ours done" | tee -a "$DRIVER"

# Baselines
for B in undefended clawguard progent taskshield; do
  OUT="$ROOT/$B"; mkdir -p "$OUT/usage" "$OUT/cases"
  echo "===== SCR $B =====" | tee -a "$DRIVER"
  for n in $NUMS; do
    cid=$(printf "case%03d" "$n")
    USAGE_DUMP_PATH="$OUT/usage/${cid}_{pid}.json" \
    $PY -m code.benchmarks.scr.execution.baselines \
      --baseline "$B" --scr-root "$SCRROOT" --manifest-file "$MANIFEST" \
      --case "$n" --condition "A+B_neutral" \
      --model "$AM" --guard-model "$AM" \
      --fusion-dataset "$FUSION" \
      --output "$OUT/cases/${cid}.json" >> "$OUT/run.log" 2>&1
  done
  echo "$B done" | tee -a "$DRIVER"
done
echo "ALL DONE" | tee -a "$DRIVER"
