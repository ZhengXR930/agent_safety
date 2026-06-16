#!/usr/bin/env python3
"""Generation eval for M2 boundary-schema LoRA."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


FIELDS = [
    "task_support",
    "source_authority_dependence",
    "untrusted_value_flow",
    "decision",
]


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def parse_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    obj = json.loads(text)
    return {
        "task_support": str(obj.get("task_support", "")).lower(),
        "source_authority_dependence": str(obj.get("source_authority_dependence", "")).lower(),
        "untrusted_value_flow": str(obj.get("untrusted_value_flow", "")).lower(),
        "decision": str(obj.get("decision", "")).upper(),
        "reasoning": str(obj.get("reasoning", "")),
    }


def render_prompt(tokenizer: Any, row: dict[str, Any]) -> str:
    user_content = row["messages"][0]["content"]
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": user_content}],
        tokenize=False,
        add_generation_prompt=True,
    )


def fit_prompt(
    tokenizer: Any,
    prompt: str,
    *,
    max_prompt_tokens: int,
    prompt_head_tokens: int,
) -> str:
    ids = tokenizer(prompt, add_special_tokens=False).input_ids
    if len(ids) <= max_prompt_tokens:
        return prompt
    if max_prompt_tokens <= prompt_head_tokens + 32:
        kept = ids[-max_prompt_tokens:]
    else:
        keep_head = min(prompt_head_tokens, max_prompt_tokens // 2)
        keep_tail = max_prompt_tokens - keep_head
        kept = ids[:keep_head] + ids[-keep_tail:]
    return tokenizer.decode(kept, skip_special_tokens=False)


def update_counts(metrics: dict[str, Any], row: dict[str, Any], pred: dict[str, Any] | None) -> None:
    label = row["label"]
    kind = row.get("kind", "unknown")
    metrics["n"] += 1
    metrics["by_kind"][kind]["n"] += 1
    if pred is None:
        metrics["parse_errors"] += 1
        metrics["by_kind"][kind]["parse_errors"] += 1
        return
    metrics["parsed"] += 1
    metrics["decision_counts"][pred["decision"]] += 1
    metrics["label_decision_counts"][label["decision"]] += 1
    metrics["by_kind"][kind]["decision_counts"][pred["decision"]] += 1
    for field in FIELDS:
        ok = pred.get(field) == label.get(field)
        metrics["field_correct"][field] += int(ok)
        metrics["by_kind"][kind]["field_correct"][field] += int(ok)
    exact = all(pred.get(field) == label.get(field) for field in FIELDS)
    metrics["exact"] += int(exact)
    metrics["by_kind"][kind]["exact"] += int(exact)


def finalize(metrics: dict[str, Any]) -> dict[str, Any]:
    n = metrics["n"]
    parsed = metrics["parsed"]
    metrics["parse_rate"] = parsed / n if n else 0.0
    metrics["exact_rate"] = metrics["exact"] / parsed if parsed else 0.0
    metrics["field_accuracy"] = {
        k: v / parsed if parsed else 0.0 for k, v in metrics["field_correct"].items()
    }
    for kind, sub in metrics["by_kind"].items():
        kn = sub["n"]
        kp = kn - sub["parse_errors"]
        sub["parse_rate"] = kp / kn if kn else 0.0
        sub["exact_rate"] = sub["exact"] / kp if kp else 0.0
        sub["field_accuracy"] = {
            k: v / kp if kp else 0.0 for k, v in sub["field_correct"].items()
        }
        allow = sub["decision_counts"].get("ALLOW", 0)
        block = sub["decision_counts"].get("BLOCK", 0)
        warn = sub["decision_counts"].get("WARN", 0)
        sub["allow_rate"] = allow / kp if kp else 0.0
        sub["warn_or_block_rate"] = (warn + block) / kp if kp else 0.0
        sub["block_rate"] = block / kp if kp else 0.0
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="MurrayTom/TS-Guard")
    parser.add_argument("--adapter-path", required=True)
    parser.add_argument("--input-jsonl", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-records", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--load-in-4bit", action="store_true")
    parser.add_argument("--max-prompt-tokens", type=int, default=4096)
    parser.add_argument("--prompt-head-tokens", type=int, default=768)
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--progress-every", type=int, default=10)
    args = parser.parse_args()

    rows = load_jsonl(args.input_jsonl)
    if args.limit is not None:
        rows = rows[: args.limit]

    tokenizer = AutoTokenizer.from_pretrained(args.adapter_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    if args.load_in_4bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        base = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            quantization_config=quant_config,
            device_map="auto",
            trust_remote_code=True,
        )
    else:
        base = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
    model = PeftModel.from_pretrained(base, args.adapter_path)
    model.eval()

    metrics: dict[str, Any] = {
        "n": 0,
        "parsed": 0,
        "parse_errors": 0,
        "exact": 0,
        "field_correct": Counter(),
        "decision_counts": Counter(),
        "label_decision_counts": Counter(),
        "by_kind": defaultdict(
            lambda: {
                "n": 0,
                "parse_errors": 0,
                "exact": 0,
                "field_correct": Counter(),
                "decision_counts": Counter(),
            }
        ),
    }

    out_records = []
    for idx, row in enumerate(rows, start=1):
        prompt = fit_prompt(
            tokenizer,
            render_prompt(tokenizer, row),
            max_prompt_tokens=args.max_prompt_tokens,
            prompt_head_tokens=args.prompt_head_tokens,
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        new_ids = output[0][inputs["input_ids"].shape[1] :]
        raw = tokenizer.decode(new_ids, skip_special_tokens=True)
        try:
            pred = parse_json(raw)
        except Exception as exc:
            pred = None
            raw = raw + f"\n[PARSE_ERROR] {exc!r}"
        update_counts(metrics, row, pred)
        out_records.append(
            {
                "eval_id": row.get("eval_id"),
                "kind": row.get("kind"),
                "label": row.get("label"),
                "prediction": pred,
                "raw": raw,
            }
        )
        if args.progress_every and idx % args.progress_every == 0:
            print(f"progress {idx}/{len(rows)}")

    final = finalize(metrics)
    serializable = json.loads(json.dumps(final, default=dict))
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.output_records:
        rec_path = Path(args.output_records)
        rec_path.parent.mkdir(parents=True, exist_ok=True)
        with rec_path.open("w", encoding="utf-8") as f:
            for rec in out_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(serializable, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
