#!/usr/bin/env bash
set -euo pipefail

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety"
LOCAL_ROOT="${ARNOLD_WORKSPACE_LOCAL_DISK_PATH:-/mnt/local/localcache00}"
MODEL_DIR="$LOCAL_ROOT/agent_safety_models/Llama-3.1-8B-Instruct"

mkdir -p "$MODEL_DIR"
cd "$ROOT"

export HF_HOME="$ROOT/.hf_cache"
export TRANSFORMERS_CACHE="$ROOT/.hf_cache/transformers"

if [[ -z "${HF_TOKEN:-}" ]]; then
  for token_file in "$HOME/.cache/huggingface/token" "$HOME/.huggingface/token" "$HOME/.autoresearch/secrets/huggingface_token" "$HOME/.codex/secrets/huggingface_token"; do
    if [[ -s "$token_file" ]]; then
      export HF_TOKEN="$(cat "$token_file")"
      break
    fi
  done
fi

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "Missing HF_TOKEN. Put it in ~/.cache/huggingface/token or export HF_TOKEN before running." >&2
  exit 2
fi

# The worker's default NO_PROXY can contain IPv6 CIDR entries that older httpx
# rejects while constructing proxy mounts. Keep HTTP(S)_PROXY but clear NO_PROXY.
unset NO_PROXY no_proxy

hf download meta-llama/Llama-3.1-8B-Instruct \
  --local-dir "$MODEL_DIR" \
  --max-workers 1

MODEL_DIR="$MODEL_DIR" python - <<'PY'
import os
from pathlib import Path

model_dir = Path(os.environ["MODEL_DIR"])
required = ["config.json", "tokenizer.json", "generation_config.json"]
missing = [name for name in required if not (model_dir / name).exists()]
files = sorted(p.relative_to(model_dir).as_posix() for p in model_dir.rglob("*") if p.is_file())
print(f"model_dir={model_dir}")
print(f"downloaded_files={len(files)}")
print(f"missing_required={missing}")
for name in files[:30]:
    print(name)
if missing:
    raise SystemExit(1)
PY
