#!/usr/bin/env bash
set -euo pipefail

cd /mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety

set -a
source config.txt
set +a

# Worker NO_PROXY contains IPv6/CIDR entries that some httpx versions parse as
# URL patterns and reject. Keep the actual proxy endpoints but sanitize no_proxy.
export NO_PROXY="localhost,127.0.0.1"
export no_proxy="${NO_PROXY}"

CATEGORY="${1:-authority}"
TARGET_KIND="${2:-tsguard}"
ADAPTER_PATH="${3:-}"
OUT_SUFFIX="${4:-${CATEGORY}_${TARGET_KIND}_sanity1}"
CUDA_VISIBLE="${CUDA_VISIBLE_DEVICES:-0}"

args=(
  python code/run_adaptive_three_category_attack.py
  --category "${CATEGORY}"
  --limit-cases 1
  --n-streams 1
  --n-iterations 1
  --target-kind "${TARGET_KIND}"
  --cuda-visible-devices "${CUDA_VISIBLE}"
  --output-dir "code/results/adaptive_three_category_sanity/${OUT_SUFFIX}"
)

if [[ -n "${ADAPTER_PATH}" ]]; then
  args+=(--adapter-path "${ADAPTER_PATH}")
fi

"${args[@]}"
