#!/usr/bin/env bash
set -euo pipefail

ROOT="/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety"
PYTHON_BIN="${PYTHON_BIN:-/home/tiger/miniconda3/envs/pytorch/bin/python}"
OUT_DIR="${OUT_DIR:-code/data/authority_teacher_gpt_full}"
LOG_DIR="${LOG_DIR:-code/results/authority_teacher_gpt_full}"

cd "${ROOT}"
mkdir -p "${OUT_DIR}" "${LOG_DIR}"

CMD=(
  env PYTHONPATH=code
  "${PYTHON_BIN}"
  code/build_authority_teacher_labels.py
  --output-dir "${OUT_DIR}"
  --bucket-limits '{"unsafe_authority_flow":1220,"broad_clean":2785,"clean_side_effect":633,"clean_value_flow":352}'
  --seed 31
  --resume
)

nohup "${CMD[@]}" > "${LOG_DIR}/label_stdout.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOG_DIR}/pid.txt"
echo "started authority full labeling pid=${PID}"
echo "labels: ${OUT_DIR}/teacher_labels.jsonl"
echo "log: ${LOG_DIR}/label_stdout.log"
