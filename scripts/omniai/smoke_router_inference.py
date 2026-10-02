"""One short local model inference; this is not a router quality benchmark."""

from __future__ import annotations

import argparse
import json
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("OMNIAI_ROUTER_MODEL"))
    parser.add_argument("--adapter")
    args = parser.parse_args()
    if not args.model:
        parser.error("Provide --model or OMNIAI_ROUTER_MODEL")
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto", dtype="auto")
    if args.adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    prompt = 'Classify this query: "Find the exact GW-01 asset record." Reply with a short JSON object.'
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=48, do_sample=False, pad_token_id=tokenizer.pad_token_id)
    output = tokenizer.decode(generated[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(json.dumps({"mode": "adapter" if args.adapter else "base", "device": str(model.device), "cuda": torch.cuda.is_available(), "generated_tokens": int(generated.shape[1] - inputs["input_ids"].shape[1]), "elapsed_seconds": round(time.perf_counter() - started, 2), "raw_output": output, "quality_claim": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
