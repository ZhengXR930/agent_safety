#!/bin/bash
cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/active_defense
export USAGE_DUMP_PATH="experiment_results/efficiency_20/DeepSeek/MCPTox/mcpguard_e2e/usage.json"
/usr/bin/python3.11 -m code.benchmarks.mcptox.execution.mcpguard_e2e \
  --model deepseek-v4-flash --evaluation-model gpt-5.4-2026-03-05 \
  --workers 8 --case-id AWSKnowledgeBase:210 --case-id Apify:245 --case-id Commander:76 --case-id DumplingAI:428 --case-id Email:176 --case-id Email:299 --case-id Email:303 --case-id FileSystem:31 --case-id Git:36 --case-id GitHub:297 --case-id GitHub:339 --case-id Memory:81 --case-id Prisma:118 --case-id Prisma:81 --case-id Prisma:91 --case-id Prisma:96 --case-id Puppeteer:117 --case-id Puppeteer:118 --case-id Puppeteer:88 --case-id Redis:166 --output "experiment_results/efficiency_20/DeepSeek/MCPTox/mcpguard_e2e/result.json"
echo "mcpguard_e2e_fix exit=$? usage=$(tr -d '\n' < "experiment_results/efficiency_20/DeepSeek/MCPTox/mcpguard_e2e/usage.json" 2>/dev/null | head -c 260)" >> "experiment_results/efficiency_20/DeepSeek/MCPTox/mcpguard_e2e/../driver.log"
