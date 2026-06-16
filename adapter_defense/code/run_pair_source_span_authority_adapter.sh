#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety"
PYTHON_BIN="${PYTHON_BIN:-/home/tiger/miniconda3/envs/pytorch/bin/python}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
LIMIT_CASES="${LIMIT_CASES:-50}"
OUTPUT_DIR="${OUTPUT_DIR:-code/results/pair_source_span_authority_adapter_${LIMIT_CASES}_deepseek}"

cd "$ROOT_DIR"

if [[ -z "${DEEPSEEK_API_KEY:-}" && -f config.txt ]]; then
  DEEPSEEK_API_KEY="$("$PYTHON_BIN" - <<'PY'
from pathlib import Path
for line in Path("config.txt").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key.strip() == "DEEPSEEK_API_KEY":
        print(value.strip().strip('"').strip("'"))
        break
PY
)"
  export DEEPSEEK_API_KEY
fi

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "Missing DEEPSEEK_API_KEY in environment or config.txt" >&2
  exit 1
fi

export CUDA_VISIBLE_DEVICES
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"

"$PYTHON_BIN" -u code/run_pair_source_span_tsguard.py \
  --target-kind authority_adapter \
  --target-model MurrayTom/TS-Guard \
  --adapter-path code/models/authority_teacher_lora_ts_guard_4bit_attn \
  --adapter-max-prompt-tokens 3072 \
  --adapter-prompt-head-tokens 512 \
  --adapter-max-new-tokens 120 \
  --cuda-visible-devices "$CUDA_VISIBLE_DEVICES" \
  --rewrite-rationale \
  --attacker-model deepseek-chat \
  --proxy-agent-model deepseek-chat \
  --allow-same-proxy-model \
  --api-key-env DEEPSEEK_API_KEY \
  --base-url https://api.deepseek.com \
  --limit-cases "$LIMIT_CASES" \
  --output-dir "$OUTPUT_DIR" \
  --resume
