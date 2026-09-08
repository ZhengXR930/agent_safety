#!/usr/bin/env bash
# Efficiency harness: MCPTox, 20 fixed attack ids, all baselines + Ours.
set -uo pipefail
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
PY=/usr/bin/python3.11
ROOT=experiment_results/efficiency_20/DeepSeek/MCPTox
mkdir -p "$ROOT"

IDS_FILE=experiment_results/efficiency_20/DeepSeek/mcptox_ids.json
CASEARGS=$($PY -c "import json;print(' '.join('--case-id '+i for i in json.load(open('$IDS_FILE'))['case_ids']))")
FROZEN=code/ours/contracts/mcptox/contracts.json
export PIPELOCK_BIN=$(readlink -f .tools/pipelock-3.2.0/pipelock)

# Ours (frozen contract, full active defense)
OUT="$ROOT/ours"; mkdir -p "$OUT"
echo "===== MCPTox ours ====="
USAGE_DUMP_PATH="$OUT/usage.json" \
$PY -m code.benchmarks.mcp_common.runtime \
  --model deepseek-v4-flash --contract-model deepseek-v4-flash \
  --evaluation-model gpt-5.4-2026-03-05 \
  --dataset mcptox --mcptox-mode attack --ablation-mode full \
  --contracts-input "$FROZEN" --frozen-contracts-only \
  --case-ids-file "$IDS_FILE" --workers 8 \
  --output "$OUT/result.json" > "$OUT/run.log" 2>&1
echo "ours exit=$? usage=$(tr -d '\n' < "$OUT/usage.json" 2>/dev/null | head -c 200)"

# Undefended
OUT="$ROOT/undefended"; mkdir -p "$OUT"
echo "===== MCPTox undefended ====="
USAGE_DUMP_PATH="$OUT/usage.json" \
$PY -m code.benchmarks.mcptox.execution.undefended \
  --model deepseek-v4-flash --evaluation-model gpt-5.4-2026-03-05 \
  --workers 8 $CASEARGS --output "$OUT/result.json" > "$OUT/run.log" 2>&1
echo "undefended exit=$? usage=$(tr -d '\n' < "$OUT/usage.json" 2>/dev/null | head -c 200)"

# Scanner baselines (share --case-id filter)
for M in clawguard_e2e mcpguard_e2e stackone_e2e pipelock; do
  OUT="$ROOT/$M"; mkdir -p "$OUT"
  echo "===== MCPTox $M ====="
  USAGE_DUMP_PATH="$OUT/usage.json" \
  $PY -m code.benchmarks.mcptox.execution.$M \
    --model deepseek-v4-flash --evaluation-model gpt-5.4-2026-03-05 \
    --workers 8 $CASEARGS --output "$OUT/result.json" > "$OUT/run.log" 2>&1
  echo "$M exit=$? usage=$(tr -d '\n' < "$OUT/usage.json" 2>/dev/null | head -c 200)"
done
echo "MCPTox efficiency DONE"
