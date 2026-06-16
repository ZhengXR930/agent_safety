#!/usr/bin/env bash
set -euo pipefail

# Train/evaluate the primary authority adapter:
#   train: existing benchmark authority-flow + benchmark clean, no PAIR
#   eval: benchmark dev/test + PAIR dev/test/all as adaptive held-out artifacts

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NPROC="${NPROC:-4}"
BASE_MODEL="${BASE_MODEL:-MurrayTom/TS-Guard}"
DATA_DIR="${DATA_DIR:-code/data/authority_nopair_adapter}"
OUT_DIR="${OUT_DIR:-code/models/authority_nopair_lora_ts_guard_4bit_attn}"
RESULT_DIR="${RESULT_DIR:-code/results/authority_nopair_lora_4bit_attn}"
FIELDS="task_authorizes_action,external_authority_used,decision"

cd "${ROOT}"

export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"

mkdir -p "${RESULT_DIR}/train_logs" "${RESULT_DIR}/eval"

torchrun --nproc_per_node="${NPROC}" code/train_m2_boundary_lora.py \
  --load-in-4bit \
  --base-model "${BASE_MODEL}" \
  --train-jsonl "${DATA_DIR}/train.jsonl" \
  --dev-jsonl "${DATA_DIR}/dev.jsonl" \
  --output-dir "${OUT_DIR}" \
  --log-jsonl "${RESULT_DIR}/train_logs/train_events.jsonl" \
  --max-seq-len "${MAX_SEQ_LEN:-3072}" \
  --prompt-head-tokens "${PROMPT_HEAD_TOKENS:-512}" \
  --num-train-epochs "${EPOCHS:-2}" \
  --learning-rate "${LR:-1e-5}" \
  --per-device-train-batch-size 1 \
  --per-device-eval-batch-size 1 \
  --gradient-accumulation-steps "${GRAD_ACCUM:-4}" \
  --lora-target attention \
  --lora-r "${LORA_R:-8}" \
  --lora-alpha "${LORA_ALPHA:-16}" \
  --lora-dropout "${LORA_DROPOUT:-0.05}" \
  --eval-steps "${EVAL_STEPS:-50}" \
  --save-steps "${SAVE_STEPS:-50}" \
  2>&1 | tee "${RESULT_DIR}/train_logs/train_stdout.log"

eval_split() {
  local name="$1"
  local input_jsonl="$2"
  CUDA_VISIBLE_DEVICES="${EVAL_CUDA_VISIBLE_DEVICES:-0}" "${PYTHON_BIN}" -u code/eval_capability_lora.py \
    --load-in-4bit \
    --base-model "${BASE_MODEL}" \
    --adapter-path "${OUT_DIR}" \
    --input-jsonl "${input_jsonl}" \
    --output-json "${RESULT_DIR}/eval/${name}_metrics.json" \
    --output-records "${RESULT_DIR}/eval/${name}_records.jsonl" \
    --fields "${FIELDS}" \
    --max-prompt-tokens "${EVAL_MAX_PROMPT_TOKENS:-3072}" \
    --prompt-head-tokens "${EVAL_PROMPT_HEAD_TOKENS:-512}" \
    --max-new-tokens "${EVAL_MAX_NEW_TOKENS:-120}" \
    --progress-every 10 \
    --resume
}

eval_split "benchmark_dev" "${DATA_DIR}/dev.jsonl"
eval_split "benchmark_test" "${DATA_DIR}/test.jsonl"
eval_split "pair_dev" "${DATA_DIR}/pair_eval/dev.jsonl"
eval_split "pair_test" "${DATA_DIR}/pair_eval/test.jsonl"
eval_split "pair_all" "${DATA_DIR}/pair_eval/all.jsonl"
