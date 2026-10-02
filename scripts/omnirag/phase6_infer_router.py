#!/usr/bin/env python3
"""Run deterministic structured inference for a base model or LoRA adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.training.dataset import load_jsonl, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="benchmarks/omnirag/phase6/router/test.jsonl")
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=160)
    args = parser.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto", dtype="auto")
    if args.adapter:
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()

    rows = load_jsonl(ROOT / args.dataset)
    predictions = []
    for row in rows:
        inputs = tokenizer(row["prompt"], return_tensors="pt").to(model.device)
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=args.max_new_tokens,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        completion_tokens = output[0, inputs["input_ids"].shape[1] :]
        text = tokenizer.decode(completion_tokens, skip_special_tokens=True).strip()
        predictions.append({"id": row["id"], "prediction": text})
    write_jsonl(ROOT / args.output, predictions)
    print(json.dumps({"rows": len(predictions), "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
