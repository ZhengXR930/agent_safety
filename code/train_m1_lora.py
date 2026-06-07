#!/usr/bin/env python3
"""M1 LoRA training for TS-Guard adaptive hardening.

This is the minimal binary/replay MVP:
- keep TS-Guard's original three-field output schema;
- train only LoRA parameters;
- mix static replay with train-split PAIR hard negatives;
- avoid train/test leakage by consuming split-aware JSONL from
  build_guard_mvp_m1_dataset.py.

Run with torchrun for 4x V100:

torchrun --nproc_per_node=4 code/train_m1_lora.py \
  --train-jsonl code/data/guard_mvp_m1/train.jsonl \
  --dev-jsonl code/data/guard_mvp_m1/dev.jsonl \
  --output-dir code/models/m1_lora
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from peft import LoraConfig, get_peft_model
from peft import prepare_model_for_kbit_training
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainerCallback,
    TrainerControl,
    TrainerState,
    Trainer,
    TrainingArguments,
    set_seed,
)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def maybe_repeat_hard_negatives(rows: list[dict[str, Any]], repeat: int) -> list[dict[str, Any]]:
    if repeat <= 1:
        return rows
    expanded: list[dict[str, Any]] = []
    for row in rows:
        expanded.append(row)
        if (row.get("meta") or {}).get("record_type") == "adaptive_hard_negative":
            expanded.extend([row] * (repeat - 1))
    return expanded


class ChatSFTDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        return self.rows[idx]


class JsonlLoggingCallback(TrainerCallback):
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, event: str, payload: dict[str, Any]) -> None:
        row = {"event": event, **payload}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def on_log(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        logs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if state.is_local_process_zero:
            self._write(
                "log",
                {
                    "step": state.global_step,
                    "epoch": state.epoch,
                    "logs": logs or {},
                },
            )

    def on_evaluate(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        metrics: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if state.is_local_process_zero:
            self._write(
                "evaluate",
                {
                    "step": state.global_step,
                    "epoch": state.epoch,
                    "metrics": metrics or {},
                },
            )

    def on_save(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs: Any,
    ) -> None:
        if state.is_local_process_zero:
            self._write("save", {"step": state.global_step, "epoch": state.epoch})


@dataclass
class ChatDataCollator:
    tokenizer: Any
    max_seq_len: int
    prompt_head_tokens: int

    def _render_prompt(self, user_content: str) -> str:
        if hasattr(self.tokenizer, "apply_chat_template"):
            return self.tokenizer.apply_chat_template(
                [{"role": "user", "content": user_content}],
                tokenize=False,
                add_generation_prompt=True,
            )
        return user_content

    def _truncate_prompt_ids(self, prompt_ids: list[int], target_len: int) -> list[int]:
        max_prompt = max(1, self.max_seq_len - target_len)
        if len(prompt_ids) <= max_prompt:
            return prompt_ids
        if max_prompt <= self.prompt_head_tokens + 32:
            return prompt_ids[-max_prompt:]
        keep_head = min(self.prompt_head_tokens, max_prompt // 2)
        keep_tail = max_prompt - keep_head
        return prompt_ids[:keep_head] + prompt_ids[-keep_tail:]

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        input_ids_batch: list[list[int]] = []
        labels_batch: list[list[int]] = []

        eos = self.tokenizer.eos_token or ""
        for item in features:
            user_content = item["messages"][0]["content"]
            assistant_content = item["messages"][1]["content"].strip()
            rendered_prompt = self._render_prompt(user_content)

            prompt_ids = self.tokenizer(rendered_prompt, add_special_tokens=False).input_ids
            target_ids = self.tokenizer(
                assistant_content + eos,
                add_special_tokens=False,
            ).input_ids
            prompt_ids = self._truncate_prompt_ids(prompt_ids, len(target_ids))
            input_ids = prompt_ids + target_ids
            labels = [-100] * len(prompt_ids) + target_ids

            if len(input_ids) > self.max_seq_len:
                overflow = len(input_ids) - self.max_seq_len
                input_ids = input_ids[overflow:]
                labels = labels[overflow:]

            input_ids_batch.append(input_ids)
            labels_batch.append(labels)

        max_len = max(len(x) for x in input_ids_batch)
        pad_id = self.tokenizer.pad_token_id
        padded_ids, padded_labels, attention = [], [], []
        for input_ids, labels in zip(input_ids_batch, labels_batch):
            pad_len = max_len - len(input_ids)
            padded_ids.append(input_ids + [pad_id] * pad_len)
            padded_labels.append(labels + [-100] * pad_len)
            attention.append([1] * len(input_ids) + [0] * pad_len)

        return {
            "input_ids": torch.tensor(padded_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention, dtype=torch.long),
            "labels": torch.tensor(padded_labels, dtype=torch.long),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="MurrayTom/TS-Guard")
    parser.add_argument("--train-jsonl", default="code/data/guard_mvp_m1/train.jsonl")
    parser.add_argument("--dev-jsonl", default="code/data/guard_mvp_m1/dev.jsonl")
    parser.add_argument("--output-dir", default="code/models/m1_lora")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-seq-len", type=int, default=4096)
    parser.add_argument("--prompt-head-tokens", type=int, default=768)
    parser.add_argument("--max-train-samples", type=int, default=None)
    parser.add_argument("--max-dev-samples", type=int, default=None)
    parser.add_argument("--hard-negative-repeat", type=int, default=3)
    parser.add_argument("--num-train-epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--per-device-eval-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--eval-steps", type=int, default=100)
    parser.add_argument("--save-steps", type=int, default=100)
    parser.add_argument("--save-total-limit", type=int, default=2)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument(
        "--lora-target",
        choices=["attention", "all"],
        default="all",
        help="Use attention-only LoRA for lower memory, or all attention+MLP projections.",
    )
    parser.add_argument("--log-jsonl", default=None)
    parser.add_argument("--load-in-4bit", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    train_rows = maybe_repeat_hard_negatives(load_jsonl(args.train_jsonl), args.hard_negative_repeat)
    dev_rows = load_jsonl(args.dev_jsonl)
    if args.max_train_samples is not None:
        train_rows = train_rows[: args.max_train_samples]
    if args.max_dev_samples is not None:
        dev_rows = dev_rows[: args.max_dev_samples]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_jsonl = Path(args.log_jsonl) if args.log_jsonl else out_dir / "train_events.jsonl"

    data_summary = {
        "train_rows_after_repeat": len(train_rows),
        "dev_rows": len(dev_rows),
        "train_sources": {},
        "train_record_types": {},
    }
    for row in train_rows:
        meta = row.get("meta") or {}
        source = meta.get("source", "unknown")
        record_type = meta.get("record_type", "unknown")
        data_summary["train_sources"][source] = data_summary["train_sources"].get(source, 0) + 1
        data_summary["train_record_types"][record_type] = (
            data_summary["train_record_types"].get(record_type, 0) + 1
        )
    (out_dir / "data_summary.json").write_text(
        json.dumps(data_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    if args.load_in_4bit:
        local_rank = int(os.environ.get("LOCAL_RANK", "0"))
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            quantization_config=quant_config,
            device_map={"": local_rank},
            trust_remote_code=True,
        )
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    else:
        model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
    model.config.use_cache = False
    if not args.load_in_4bit:
        model.gradient_checkpointing_enable()

    if args.lora_target == "attention":
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]
    else:
        target_modules = [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target_modules,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    data_collator = ChatDataCollator(
        tokenizer=tokenizer,
        max_seq_len=args.max_seq_len,
        prompt_head_tokens=args.prompt_head_tokens,
    )

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.num_train_epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        warmup_ratio=args.warmup_ratio,
        fp16=True,
        bf16=False,
        gradient_checkpointing=True,
        logging_steps=args.logging_steps,
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        report_to=[],
        remove_unused_columns=False,
        ddp_find_unused_parameters=False,
        log_level="info",
        logging_first_step=True,
    )

    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": ChatSFTDataset(train_rows),
        "eval_dataset": ChatSFTDataset(dev_rows),
        "data_collator": data_collator,
        "callbacks": [JsonlLoggingCallback(log_jsonl)],
    }
    trainer_sig = inspect.signature(Trainer.__init__)
    if "processing_class" in trainer_sig.parameters:
        trainer_kwargs["processing_class"] = tokenizer
    elif "tokenizer" in trainer_sig.parameters:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = Trainer(**trainer_kwargs)
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    run_meta = {
        "base_model": args.base_model,
        "train_jsonl": args.train_jsonl,
        "dev_jsonl": args.dev_jsonl,
        "train_rows_after_repeat": len(train_rows),
        "dev_rows": len(dev_rows),
        "log_jsonl": str(log_jsonl),
        "data_summary": data_summary,
        "args": vars(args),
    }
    (out_dir / "run_meta.json").write_text(
        json.dumps(run_meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
