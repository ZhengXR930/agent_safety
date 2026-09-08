#!/bin/bash
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
OUT=experiment_results/efficiency_20/DeepSeek/MCPTox/ours_fullcost
export USAGE_DUMP_PATH="$OUT/usage.json"
/usr/bin/python3.11 -m code.benchmarks.mcp_common.runtime \
  --model deepseek-v4-flash --contract-model deepseek-v4-flash \
  --evaluation-model gpt-5.4-2026-03-05 \
  --dataset mcptox --mcptox-mode attack --ablation-mode full \
  --case-ids-file experiment_results/efficiency_20/DeepSeek/mcptox_ids.json \
  --workers 8 --output "$OUT/result.json"
echo "ours_fullcost exit=$? usage=$(tr -d '\n' < "$OUT/usage.json" 2>/dev/null | head -c 260)" >> "$OUT/../driver.log"
