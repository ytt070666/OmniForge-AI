#!/usr/bin/env python3
"""LoRA/QLoRA SFT entrypoint for the advisory OmniRAG control router.

The training environment is intentionally separate from the RAGFlow runtime.
Use --preflight-only before allocating a GPU. No model is downloaded when that
flag is used.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.training.dataset import load_jsonl, validate_rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_status() -> dict[str, str | None]:
    packages = ["transformers", "peft", "trl", "datasets", "accelerate", "bitsandbytes", "torch"]
    out = {}
    for name in packages:
        try:
            out[name] = md.version(name)
        except md.PackageNotFoundError:
            out[name] = None
    return out


def validate_config(config: dict) -> None:
    if config.get("task_name") != "omnirag_advisory_control_router":
        raise ValueError("unexpected task_name")
    if config.get("method") not in {"lora", "qlora"}:
        raise ValueError("method must be lora or qlora")
    boundary = config.get("safety_boundary", {})
    required_false = [
        "may_authorize_write_tools",
        "may_authorize_execute_tools",
        "may_bypass_phase5_policy",
        "may_replace_phase3_evidence_verifier",
    ]
    if boundary.get("advisory_only") is not True or any(boundary.get(key) is not False for key in required_false):
        raise ValueError("safety boundary must keep the trained router advisory-only")


def preflight(config_path: Path, *, require_training_packages: bool) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    datasets = {}
    for split in ("train", "validation", "test"):
        path = ROOT / config["dataset"][split]
        if not path.exists():
            raise FileNotFoundError(path)
        rows = load_jsonl(path)
        validate_rows(rows, split_name=split)
        datasets[split] = {"rows": len(rows), "sha256": sha256(path)}
    manifest = ROOT / config["dataset"]["lineage_manifest"]
    if not manifest.exists():
        raise FileNotFoundError(manifest)
    pkgs = package_status()
    if require_training_packages:
        missing = [name for name, version in pkgs.items() if version is None]
        if missing:
            raise RuntimeError(
                "missing Phase-6 training dependencies: " + ", ".join(missing) + ". "
                "Create a separate environment using config/omnirag/phase6/requirements-training.txt and install platform PyTorch."
            )
    return {"config": config, "datasets": datasets, "packages": pkgs, "lineage_manifest_sha256": sha256(manifest)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/omnirag/phase6/router_sft.json")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume-from-checkpoint", default=None)
    args = parser.parse_args()

    config_path = ROOT / args.config
    info = preflight(config_path, require_training_packages=not args.preflight_only)
    if args.preflight_only:
        print(json.dumps(info, ensure_ascii=False, indent=2, sort_keys=True))
        print("PASS: dataset/config preflight completed; no model downloaded and no training started")
        return

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    config = info["config"]
    if not torch.cuda.is_available():
        raise RuntimeError("Phase-6 QLoRA training requires a configured accelerator; CUDA is not available")
    if config["sft"].get("bf16", False) and not torch.cuda.is_bf16_supported():
        raise RuntimeError("bf16=true but the active CUDA device does not report BF16 support; adjust the config explicitly")

    model_id = config["model_name_or_path"]
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = {"device_map": "auto", "dtype": torch.bfloat16 if config["sft"].get("bf16", False) else "auto"}
    if config["method"] == "qlora":
        q = config["qlora"]
        compute_dtype = torch.bfloat16 if q["bnb_4bit_compute_dtype"] == "bfloat16" else torch.float16
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=bool(q["load_in_4bit"]),
            bnb_4bit_quant_type=q["bnb_4bit_quant_type"],
            bnb_4bit_use_double_quant=bool(q["bnb_4bit_use_double_quant"]),
            bnb_4bit_compute_dtype=compute_dtype,
        )
    model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    if config["method"] == "qlora":
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=config["sft"].get("gradient_checkpointing", True))

    lc = config["lora"]
    peft_config = LoraConfig(
        r=int(lc["r"]),
        lora_alpha=int(lc["lora_alpha"]),
        lora_dropout=float(lc["lora_dropout"]),
        target_modules=lc["target_modules"],
        bias=lc["bias"],
        task_type=lc["task_type"],
    )

    train_ds = load_dataset("json", data_files=str(ROOT / config["dataset"]["train"]), split="train")
    eval_ds = load_dataset("json", data_files=str(ROOT / config["dataset"]["validation"]), split="train")
    s = config["sft"]
    output_dir = ROOT / config["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    sft_args = SFTConfig(
        output_dir=str(output_dir),
        num_train_epochs=float(s["num_train_epochs"]),
        per_device_train_batch_size=int(s["per_device_train_batch_size"]),
        per_device_eval_batch_size=int(s["per_device_eval_batch_size"]),
        gradient_accumulation_steps=int(s["gradient_accumulation_steps"]),
        learning_rate=float(s["learning_rate"]),
        weight_decay=float(s["weight_decay"]),
        # Transformers 5 / TRL 1.14 accepts a fractional warmup_steps value
        # and interprets it as the share of total training steps.
        warmup_steps=float(s["warmup_ratio"]),
        logging_steps=int(s["logging_steps"]),
        save_strategy=s["save_strategy"],
        eval_strategy=s["eval_strategy"],
        max_length=int(s["max_length"]),
        seed=int(s["seed"]),
        gradient_checkpointing=bool(s["gradient_checkpointing"]),
        bf16=bool(s["bf16"]),
        report_to=s["report_to"],
        completion_only_loss=True,
    )
    trainer = SFTTrainer(
        model=model,
        args=sft_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    run_manifest = {
        "schema_version": 1,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "task": config["task_name"],
        "method": config["method"],
        "base_model": model_id,
        "config_sha256": sha256(config_path),
        "datasets": info["datasets"],
        "packages": package_status(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cuda_device": torch.cuda.get_device_name(0),
        "cuda_capability": list(torch.cuda.get_device_capability(0)),
        "safety_boundary": config["safety_boundary"],
    }
    (output_dir / "omnirag_training_run_manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Training complete. Adapter: {output_dir}")


if __name__ == "__main__":
    main()
