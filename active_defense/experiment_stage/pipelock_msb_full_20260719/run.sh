#!/usr/bin/env bash
set -euo pipefail

export PATH="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/benchmarks/external/defender/.runtime/node-v22.17.0-linux-x64/bin:${PATH}"
export PIPELOCK_BIN="/tmp/pipelock-baseline-audit/pipelock"
export PIPELOCK_CONFIG="/tmp/pipelock-balanced.yaml"
export MCP_USE_ANONYMIZED_TELEMETRY=false

cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/benchmarks/external/MSB
.venv311/bin/python agent_attack.py --cfg_path config/full_pipelock.yml
