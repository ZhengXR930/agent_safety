#!/usr/bin/env python3
"""Static generation eval for an M1 LoRA/merged TS-Guard checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import torch
from peft import PeftModel
from sklearn.metrics import accuracy_score, f1_score, recall_score
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
TOOLSAFE_SRC = ROOT / "benchmarks" / "ToolSafe" / "src"
sys.path.insert(0, str(TOOLSAFE_SRC))

from utils.guardian_parser import guardian_paser_map  # noqa: E402
from utils.guardian_score_mapping import filter_valid_pairs  # noqa: E402


def load_jsonl(path: str | Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
    return rows


def render_prompt(tokenizer: Any, user_content: str) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": user_content}],
            tokenize=False,
            add_generation_prompt=True,
        )
    return user_content


def truncate_ids(ids: list[int], max_len: int, head: int) -> list[int]:
    if len(ids) <= max_len:
        return ids
    if max_len <= head + 32:
        return ids[-max_len:]
    tail = max_len - head
    return ids[:head] + ids[-tail:]


def parse_gold(text: str) -> float | None:
    pred, _ = guardian_paser_map["TS-Guard"](text)
    return pred if pred in [0, 0.0, 0.5, 1, 1.0] else None


def compute_metrics(preds: list[Any], labels: list[Any], mode: str) -> dict[str, Any]:
    p, y = filter_valid_pairs(preds, labels, score_mode=mode)
    if not y:
        return {"total": 0, "accuracy": None, "f1": None, "recall": None}
    avg = "macro" if mode == "exact" else "binary"
    return {
        "total": len(y),
        "accuracy": accuracy_score(y, p),
        "f1": f1_score(y, p, average=avg),
        "recall": recall_score(y, p, average=avg),
    }


def write_metrics(
    output_path: Path,
    args: argparse.Namespace,
    rows_seen: int,
    total_rows: int,
    preds: list[Any],
    labels: list[Any],
    complete: bool,
) -> None:
    metrics = {
        "input_jsonl": args.input_jsonl,
        "base_model": args.base_model,
        "adapter_path": args.adapter_path,
        "merged_model": args.merged_model,
        "n": rows_seen,
        "total_rows": total_rows,
        "complete": complete,
        "strict": compute_metrics(preds, labels, "strict"),
        "loose": compute_metrics(preds, labels, "loose"),
        "exact": compute_metrics(preds, labels, "exact"),
        "parse_errors": sum(p is None for p in preds),
    }
    output_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")


def load_existing_records(records_path: Path) -> tuple[list[Any], list[Any], int]:
    preds, labels = [], []
    if not records_path.exists():
        return preds, labels, 0
    with records_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            preds.append(rec.get("prediction"))
            labels.append(rec.get("label"))
    return preds, labels, len(preds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="MurrayTom/TS-Guard")
    parser.add_argument("--adapter-path", default=None)
    parser.add_argument("--merged-model", default=None)
    parser.add_argument("--input-jsonl", default="code/data/guard_mvp_m1/dev.jsonl")
    parser.add_argument("--output-json", default="code/results/m1_lora_static_eval/dev_metrics.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-prompt-tokens", type=int, default=7600)
    parser.add_argument("--prompt-head-tokens", type=int, default=1536)
    parser.add_argument("--max-new-tokens", type=int, default=96)
    parser.add_argument("--progress-every", type=int, default=20)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = args.merged_model or args.base_model
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    if args.adapter_path:
        model = PeftModel.from_pretrained(model, args.adapter_path)
    model.eval()

    rows = load_jsonl(args.input_jsonl, args.limit)
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records_path = output_path.with_suffix(".records.jsonl")

    if args.resume:
        preds, labels, completed = load_existing_records(records_path)
        if completed > len(rows):
            raise ValueError(f"Existing records ({completed}) exceed input rows ({len(rows)}): {records_path}")
        if completed:
            print(f"resume from {completed}/{len(rows)}", flush=True)
    else:
        preds, labels, completed = [], [], 0
        if records_path.exists():
            records_path.unlink()

    records_file = records_path.open("a", encoding="utf-8")

    for start in range(completed, len(rows), args.batch_size):
        batch = rows[start : start + args.batch_size]
        prompt_ids = []
        for row in batch:
            prompt = render_prompt(tokenizer, row["messages"][0]["content"])
            ids = tokenizer(prompt, add_special_tokens=False).input_ids
            ids = truncate_ids(ids, args.max_prompt_tokens, args.prompt_head_tokens)
            prompt_ids.append(ids)
        max_len = max(len(x) for x in prompt_ids)
        input_ids, attention = [], []
        for ids in prompt_ids:
            pad = [tokenizer.pad_token_id] * (max_len - len(ids))
            input_ids.append(pad + ids)
            attention.append([0] * len(pad) + [1] * len(ids))
        input_tensor = torch.tensor(input_ids, dtype=torch.long, device=model.device)
        attn_tensor = torch.tensor(attention, dtype=torch.long, device=model.device)
        with torch.no_grad():
            out = model.generate(
                input_ids=input_tensor,
                attention_mask=attn_tensor,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        for row, generated, ids in zip(batch, out, input_ids):
            new_tokens = generated[len(ids) :]
            text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
            pred, details = guardian_paser_map["TS-Guard"](text)
            gold = parse_gold(row["messages"][1]["content"])
            preds.append(pred if pred in [0, 0.0, 0.5, 1, 1.0] else None)
            labels.append(gold)
            rec = {
                "row_index": len(preds) - 1,
                "meta": row.get("meta", {}),
                "prediction": preds[-1],
                "label": gold,
                "details": details,
                "output": text,
            }
            records_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
        records_file.flush()
        done = min(start + len(batch), len(rows))
        if args.progress_every > 0 and (done == len(rows) or done % args.progress_every == 0):
            write_metrics(output_path, args, done, len(rows), preds, labels, complete=(done == len(rows)))
            print(f"progress {done}/{len(rows)}", flush=True)
    records_file.close()
    write_metrics(output_path, args, len(rows), len(rows), preds, labels, complete=True)
    print(output_path.read_text(encoding="utf-8"))
    print(records_path)


if __name__ == "__main__":
    main()
