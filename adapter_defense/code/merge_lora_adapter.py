#!/usr/bin/env python3
"""Merge a PEFT LoRA adapter into a base causal LM checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="MurrayTom/TS-Guard")
    parser.add_argument("--adapter-path", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, args.adapter_path)
    model = model.merge_and_unload()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out, safe_serialization=True)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    tokenizer.save_pretrained(out)
    print(out)


if __name__ == "__main__":
    main()
