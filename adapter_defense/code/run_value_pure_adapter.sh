#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety"
PYTHON_BIN="${PYTHON_BIN:-/home/tiger/miniconda3/envs/pytorch/bin/python}"
NPROC="${NPROC:-4}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3}"

cd "$ROOT_DIR"

export CUDA_VISIBLE_DEVICES
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"

MODEL_DIR="${MODEL_DIR:-code/models/value_pure_lora_ts_guard_4bit_attn}"
LOG_DIR="${LOG_DIR:-code/results/value_pure_lora_4bit_attn}"
mkdir -p "$LOG_DIR/train_logs" "$LOG_DIR/eval"

torchrun --nproc_per_node="$NPROC" code/train_m2_boundary_lora.py \
  --load-in-4bit \
  --base-model MurrayTom/TS-Guard \
  --train-jsonl code/data/value_pure_sft_balanced_1p2k/train.jsonl \
  --dev-jsonl code/data/value_pure_sft_balanced_1p2k/dev.jsonl \
  --output-dir "$MODEL_DIR" \
  --log-jsonl "$LOG_DIR/train_logs/train_events.jsonl" \
  --max-seq-len 3072 \
  --prompt-head-tokens 512 \
  --num-train-epochs 2 \
  --learning-rate 1e-5 \
  --per-device-train-batch-size 1 \
  --per-device-eval-batch-size 1 \
  --gradient-accumulation-steps 4 \
  --lora-target attention \
  --lora-r 8 \
  --lora-alpha 16 \
  --lora-dropout 0.05 \
  --eval-steps 50 \
  --save-steps 50 \
  2>&1 | tee "$LOG_DIR/train_logs/train_stdout.log"

CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" -u code/eval_capability_lora.py \
  --load-in-4bit \
  --base-model MurrayTom/TS-Guard \
  --adapter-path "$MODEL_DIR" \
  --input-jsonl code/data/value_pure_sft_balanced_1p2k/dev.jsonl \
  --output-json "$LOG_DIR/eval/dev_metrics.json" \
  --output-records "$LOG_DIR/eval/dev_records.jsonl" \
  --fields action_in_user_scope,values_in_user_scope,sensitive_value_from_untrusted_source,decision \
  --max-prompt-tokens 3072 \
  --prompt-head-tokens 512 \
  --max-new-tokens 140 \
  --progress-every 10 \
  --resume

CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" -u code/eval_capability_lora.py \
  --load-in-4bit \
  --base-model MurrayTom/TS-Guard \
  --adapter-path "$MODEL_DIR" \
  --input-jsonl code/data/value_pure_sft_balanced_1p2k/test.jsonl \
  --output-json "$LOG_DIR/eval/test_metrics.json" \
  --output-records "$LOG_DIR/eval/test_records.jsonl" \
  --fields action_in_user_scope,values_in_user_scope,sensitive_value_from_untrusted_source,decision \
  --max-prompt-tokens 3072 \
  --prompt-head-tokens 512 \
  --max-new-tokens 140 \
  --progress-every 10 \
  --resume
