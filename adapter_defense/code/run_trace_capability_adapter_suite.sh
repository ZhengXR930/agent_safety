#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash code/run_trace_capability_adapter_suite.sh value
#   bash code/run_trace_capability_adapter_suite.sh authority
#   bash code/run_trace_capability_adapter_suite.sh policy
#   bash code/run_trace_capability_adapter_suite.sh all
#
# Required: run on a GPU worker where torch.cuda.is_available() is true.

CAPABILITY="${1:-all}"
ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NPROC="${NPROC:-4}"
BASE_MODEL="${BASE_MODEL:-MurrayTom/TS-Guard}"
DATA_ROOT="${DATA_ROOT:-code/data/trace_capability_adapters}"
MODEL_ROOT="${MODEL_ROOT:-code/models/trace_capability_adapters}"
RESULT_ROOT="${RESULT_ROOT:-code/results/trace_capability_adapters}"

cd "${ROOT}"

export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export NCCL_DEBUG="${NCCL_DEBUG:-WARN}"

train_one() {
  local cap="$1"
  local fields="$2"
  local epochs="$3"
  local out_dir="${MODEL_ROOT}/${cap}_lora_ts_guard_4bit_attn"
  local log_dir="${RESULT_ROOT}/${cap}_train_logs"
  mkdir -p "${log_dir}" "${RESULT_ROOT}/${cap}_eval"

  echo "[train] capability=${cap} epochs=${epochs}"
  torchrun --nproc_per_node="${NPROC}" code/train_m2_boundary_lora.py \
    --load-in-4bit \
    --base-model "${BASE_MODEL}" \
    --train-jsonl "${DATA_ROOT}/${cap}/train.jsonl" \
    --dev-jsonl "${DATA_ROOT}/${cap}/dev.jsonl" \
    --output-dir "${out_dir}" \
    --log-jsonl "${log_dir}/train_events.jsonl" \
    --max-seq-len "${MAX_SEQ_LEN:-3072}" \
    --prompt-head-tokens "${PROMPT_HEAD_TOKENS:-512}" \
    --num-train-epochs "${epochs}" \
    --learning-rate "${LR:-1e-5}" \
    --per-device-train-batch-size 1 \
    --per-device-eval-batch-size 1 \
    --gradient-accumulation-steps "${GRAD_ACCUM:-4}" \
    --lora-target attention \
    --lora-r "${LORA_R:-8}" \
    --lora-alpha "${LORA_ALPHA:-16}" \
    --lora-dropout "${LORA_DROPOUT:-0.05}" \
    --eval-steps "${EVAL_STEPS:-25}" \
    --save-steps "${SAVE_STEPS:-25}" \
    2>&1 | tee "${log_dir}/train_stdout.log"

  echo "[eval-dev] capability=${cap}"
  CUDA_VISIBLE_DEVICES="${EVAL_CUDA_VISIBLE_DEVICES:-0}" "${PYTHON_BIN}" -u code/eval_capability_lora.py \
    --load-in-4bit \
    --base-model "${BASE_MODEL}" \
    --adapter-path "${out_dir}" \
    --input-jsonl "${DATA_ROOT}/${cap}/dev.jsonl" \
    --output-json "${RESULT_ROOT}/${cap}_eval/dev_metrics.json" \
    --output-records "${RESULT_ROOT}/${cap}_eval/dev_records.jsonl" \
    --fields "${fields}" \
    --max-prompt-tokens "${EVAL_MAX_PROMPT_TOKENS:-3072}" \
    --prompt-head-tokens "${EVAL_PROMPT_HEAD_TOKENS:-512}" \
    --max-new-tokens "${EVAL_MAX_NEW_TOKENS:-120}" \
    --progress-every 10 \
    --resume

  echo "[eval-test] capability=${cap}"
  CUDA_VISIBLE_DEVICES="${EVAL_CUDA_VISIBLE_DEVICES:-0}" "${PYTHON_BIN}" -u code/eval_capability_lora.py \
    --load-in-4bit \
    --base-model "${BASE_MODEL}" \
    --adapter-path "${out_dir}" \
    --input-jsonl "${DATA_ROOT}/${cap}/test.jsonl" \
    --output-json "${RESULT_ROOT}/${cap}_eval/test_metrics.json" \
    --output-records "${RESULT_ROOT}/${cap}_eval/test_records.jsonl" \
    --fields "${fields}" \
    --max-prompt-tokens "${EVAL_MAX_PROMPT_TOKENS:-3072}" \
    --prompt-head-tokens "${EVAL_PROMPT_HEAD_TOKENS:-512}" \
    --max-new-tokens "${EVAL_MAX_NEW_TOKENS:-120}" \
    --progress-every 10 \
    --resume
}

run_capability() {
  local cap="$1"
  case "${cap}" in
    value)
      train_one "value" "task_authorizes_action,task_authorizes_values,external_authority_used,decision" "${VALUE_EPOCHS:-4}"
      ;;
    authority)
      train_one "authority" "task_authorizes_action,external_authority_used,decision" "${AUTHORITY_EPOCHS:-3}"
      ;;
    policy)
      train_one "policy" "task_authorizes_action,policy_allows_action,decision" "${POLICY_EPOCHS:-2}"
      ;;
    *)
      echo "Unknown capability: ${cap}" >&2
      exit 2
      ;;
  esac
}

case "${CAPABILITY}" in
  all)
    run_capability value
    run_capability authority
    run_capability policy
    ;;
  value|authority|policy)
    run_capability "${CAPABILITY}"
    ;;
  *)
    echo "Usage: bash code/run_trace_capability_adapter_suite.sh {value|authority|policy|all}" >&2
    exit 2
    ;;
esac
