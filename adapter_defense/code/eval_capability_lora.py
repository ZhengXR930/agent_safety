#!/usr/bin/env python3
"""Generic generation eval for capability-specific LoRA adapters."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_done_records(path: str | Path | None) -> tuple[set[str], list[dict[str, Any]]]:
    if not path:
        return set(), []
    rec_path = Path(path)
    if not rec_path.exists():
        return set(), []
    done: set[str] = set()
    records: list[dict[str, Any]] = []
    with rec_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            eval_id = rec.get("eval_id")
            if eval_id is not None:
                done.add(str(eval_id))
            records.append(rec)
    return done, records


def parse_json(text: str, fields: list[str]) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    obj = json.loads(text)
    norm = {re.sub(r"[^a-zA-Z0-9_]", "_", str(k)).lower(): v for k, v in obj.items()}
    pred = {}
    for field in fields:
        val = str(norm.get(field, ""))
        pred[field] = val.upper() if field == "decision" else val.lower()
    pred["reasoning"] = str(norm.get("reasoning", ""))
    return pred


def fit_prompt(tokenizer: Any, prompt: str, max_prompt_tokens: int, prompt_head_tokens: int) -> str:
    ids = tokenizer(prompt, add_special_tokens=False).input_ids
    if len(ids) <= max_prompt_tokens:
        return prompt
    if max_prompt_tokens <= prompt_head_tokens + 32:
        kept = ids[-max_prompt_tokens:]
    else:
        keep_head = min(prompt_head_tokens, max_prompt_tokens // 2)
        kept = ids[:keep_head] + ids[-(max_prompt_tokens - keep_head) :]
    return tokenizer.decode(kept, skip_special_tokens=False)


def render_prompt(tokenizer: Any, row: dict[str, Any]) -> str:
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": row["messages"][0]["content"]}],
        tokenize=False,
        add_generation_prompt=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", default="MurrayTom/TS-Guard")
    ap.add_argument("--adapter-path", required=True)
    ap.add_argument("--input-jsonl", required=True)
    ap.add_argument("--output-json", required=True)
    ap.add_argument("--output-records", default=None)
    ap.add_argument("--fields", required=True, help="Comma-separated output fields including decision.")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--load-in-4bit", action="store_true")
    ap.add_argument("--max-prompt-tokens", type=int, default=3072)
    ap.add_argument("--prompt-head-tokens", type=int, default=512)
    ap.add_argument("--max-new-tokens", type=int, default=120)
    ap.add_argument("--progress-every", type=int, default=10)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    fields = [x.strip() for x in args.fields.split(",") if x.strip()]
    if "decision" not in fields:
        raise ValueError("--fields must include decision")

    rows = load_jsonl(args.input_jsonl)
    if args.limit is not None:
        rows = rows[: args.limit]
    done_ids: set[str] = set()
    prior_records: list[dict[str, Any]] = []
    if args.resume:
        done_ids, prior_records = load_done_records(args.output_records)
        if done_ids:
            rows = [row for row in rows if str(row.get("eval_id")) not in done_ids]
            print(f"resume: loaded {len(done_ids)} completed records, remaining {len(rows)}", flush=True)

    print("loading tokenizer", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.adapter_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    print("loading model", flush=True)
    print(f"cuda_available={torch.cuda.is_available()} cuda_count={torch.cuda.device_count()}", flush=True)
    if args.load_in_4bit and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not visible; 4bit eval would run on CPU and appear to hang.")
    device_map: Any = {"": 0} if torch.cuda.is_available() else "auto"
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
            device_map=device_map,
            trust_remote_code=True,
        )
    else:
        base = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            torch_dtype=torch.float16,
            device_map=device_map,
            trust_remote_code=True,
        )
    model = PeftModel.from_pretrained(base, args.adapter_path)
    model.eval()
    print(f"model loaded device_map={getattr(model, 'hf_device_map', None)}", flush=True)

    metrics: dict[str, Any] = {
        "n": 0,
        "parsed": 0,
        "parse_errors": 0,
        "exact": 0,
        "field_correct": Counter(),
        "decision_counts": Counter(),
        "by_kind": defaultdict(lambda: {"n": 0, "parse_errors": 0, "exact": 0, "field_correct": Counter(), "decision_counts": Counter()}),
    }

    records = list(prior_records)
    rec_f = None
    if args.output_records:
        out_rec = Path(args.output_records)
        out_rec.parent.mkdir(parents=True, exist_ok=True)
        rec_f = out_rec.open("a" if args.resume else "w", encoding="utf-8")

    for idx, row in enumerate(rows, start=1):
        prompt = fit_prompt(tokenizer, render_prompt(tokenizer, row), args.max_prompt_tokens, args.prompt_head_tokens)
        if args.progress_every and (idx == 1 or idx % args.progress_every == 0):
            prompt_tokens = len(tokenizer(prompt, add_special_tokens=False).input_ids)
            print(f"generating {idx}/{len(rows)} prompt_tokens={prompt_tokens}", flush=True)
        model_device = next(model.parameters()).device
        inputs = tokenizer(prompt, return_tensors="pt").to(model_device)
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        raw = tokenizer.decode(output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        try:
            pred = parse_json(raw, fields)
        except Exception as exc:
            pred = None
            raw = raw + f"\n[PARSE_ERROR] {exc!r}"

        kind = row.get("kind", "unknown")
        label = row["label"]
        metrics["n"] += 1
        metrics["by_kind"][kind]["n"] += 1
        if pred is None:
            metrics["parse_errors"] += 1
            metrics["by_kind"][kind]["parse_errors"] += 1
        else:
            metrics["parsed"] += 1
            metrics["decision_counts"][pred.get("decision", "")] += 1
            metrics["by_kind"][kind]["decision_counts"][pred.get("decision", "")] += 1
            exact = True
            for field in fields:
                ok = pred.get(field) == label.get(field)
                metrics["field_correct"][field] += int(ok)
                metrics["by_kind"][kind]["field_correct"][field] += int(ok)
                exact = exact and ok
            metrics["exact"] += int(exact)
            metrics["by_kind"][kind]["exact"] += int(exact)
        rec = {"eval_id": row.get("eval_id"), "kind": kind, "label": label, "prediction": pred, "raw": raw}
        records.append(rec)
        if rec_f is not None:
            rec_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            rec_f.flush()
        if args.progress_every and idx % args.progress_every == 0:
            print(f"progress {idx}/{len(rows)}", flush=True)
    if rec_f is not None:
        rec_f.close()

    parsed = metrics["parsed"]
    metrics["parse_rate"] = parsed / metrics["n"] if metrics["n"] else 0.0
    metrics["exact_rate"] = metrics["exact"] / parsed if parsed else 0.0
    metrics["field_accuracy"] = {k: v / parsed if parsed else 0.0 for k, v in metrics["field_correct"].items()}
    for _, sub in metrics["by_kind"].items():
        kp = sub["n"] - sub["parse_errors"]
        sub["parse_rate"] = kp / sub["n"] if sub["n"] else 0.0
        sub["exact_rate"] = sub["exact"] / kp if kp else 0.0
        sub["field_accuracy"] = {k: v / kp if kp else 0.0 for k, v in sub["field_correct"].items()}
        allow = sub["decision_counts"].get("ALLOW", 0)
        warn = sub["decision_counts"].get("WARN", 0)
        block = sub["decision_counts"].get("BLOCK", 0)
        sub["allow_rate"] = allow / kp if kp else 0.0
        sub["warn_or_block_rate"] = (warn + block) / kp if kp else 0.0
        sub["block_rate"] = block / kp if kp else 0.0

    serializable = json.loads(json.dumps(metrics, default=dict))
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.output_records:
        out_rec = Path(args.output_records)
        out_rec.parent.mkdir(parents=True, exist_ok=True)
        with out_rec.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(serializable, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
