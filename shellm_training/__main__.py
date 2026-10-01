"""Run a single explicit, reproducible LoRA experiment on a checked data release."""

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import random
import time
from zoneinfo import ZoneInfo

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup

from shellbench.sandbox import ROOT
from shellm_data.core import DATA, load_release
from .data import collate, tokenize_record


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validation_loss(model, examples, batch_size, pad_id):
    model.eval()
    total, tokens = 0.0, 0
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
        for index in range(0, len(examples), batch_size):
            batch = collate(examples[index:index + batch_size], pad_id)
            count = int(batch["labels"][:, 1:].ne(-100).sum())
            total += float(model(**batch).loss) * count
            tokens += count
    model.train()
    return total / tokens


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/training/lora-pilot-v1.json")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id):
        raise SystemExit("Use a lowercase run ID containing letters, digits, hyphens, and underscores")
    config = json.loads(Path(args.config).read_text())
    records, manifest = load_release(config["dataset_release"])
    validation_path = DATA / "releases" / config["dataset_release"] / "validation.json"
    validation = json.loads(validation_path.read_text())
    if not validation["all_passed"] or validation["dataset_sha256"] != manifest["dataset_sha256"]:
        raise SystemExit("Dataset lacks matching successful functional validation")
    expected_validator = hashlib.sha256((ROOT / "shellm_data" / "intents.py").read_bytes()).hexdigest()
    if validation["validator_sha256"] != expected_validator:
        raise SystemExit("Dataset validator changed; rerun functional data validation")
    report_dir, weight_dir = ROOT / "reports" / args.run_id, ROOT / "checkpoints" / args.run_id
    if report_dir.exists() or weight_dir.exists():
        raise SystemExit("Run ID already exists; earlier experiment records are preserved")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this training configuration")
    torch.manual_seed(config["seed"])
    random.seed(config["seed"])
    tokenizer = AutoTokenizer.from_pretrained(config["model"], revision=config["revision"])
    train = [tokenize_record(tokenizer, row, config["max_length"]) for row in records if row["split"] == "train"]
    dev = [tokenize_record(tokenizer, row, config["max_length"]) for row in records if row["split"] == "validation"]
    model = AutoModelForCausalLM.from_pretrained(config["model"], revision=config["revision"], dtype=torch.float16).to("cuda")
    model.config.use_cache = False
    for target in config["lora"]["target_modules"]:
        if not any(name.endswith("." + target) for name, _ in model.named_modules()):
            raise ValueError(f"Missing LoRA target: {target}")
    model = get_peft_model(model, LoraConfig(**config["lora"], revision=config["revision"]))
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    for parameter in parameters:
        parameter.data = parameter.data.float()
    trainable = sum(parameter.numel() for parameter in parameters)
    total_parameters = sum(parameter.numel() for parameter in model.parameters())
    print(f"Training {trainable:,}/{total_parameters:,} parameters ({100 * trainable / total_parameters:.2f}%)", flush=True)
    before = [parameter.detach().clone() for parameter in parameters if parameter.numel() < 100000]
    micro, effective = config["micro_batch_size"], config["effective_batch_size"]
    if effective % micro:
        raise ValueError("effective_batch_size must be divisible by micro_batch_size")
    updates_per_epoch = math.ceil(len(train) / effective)
    optimizer = torch.optim.AdamW(parameters, lr=config["learning_rate"], weight_decay=config["weight_decay"])
    scheduler = get_cosine_schedule_with_warmup(optimizer, config["warmup_steps"], updates_per_epoch * config["epochs"])
    scaler = torch.amp.GradScaler("cuda")
    report_dir.mkdir(parents=True)
    weight_dir.mkdir(parents=True)
    metadata = {
        "run_id": args.run_id, "started": datetime.now(ZoneInfo("Europe/Budapest")).isoformat(), "config": config,
        "dataset_sha256": manifest["dataset_sha256"], "train_examples": len(train), "validation_examples": len(dev),
        "trainable_parameters": trainable, "total_parameters": total_parameters,
        "gpu": torch.cuda.get_device_name(0), "max_example_tokens": max(len(row["input_ids"]) for row in train + dev),
        "packages": {name: importlib.metadata.version(name) for name in ("torch", "transformers", "peft", "accelerate")},
        "trainer_sha256": hashlib.sha256(Path(__file__).read_bytes() + Path(__file__).with_name("data.py").read_bytes()).hexdigest(),
        "precision": "FP16 frozen base and autocast, FP32 adapters and optimizer", "status": "running",
    }
    write_json(report_dir / "training-metadata.json", metadata)
    log = (report_dir / "training-log.jsonl").open("w", encoding="utf-8", buffering=1)
    started, step, examples_seen, skipped = time.perf_counter(), 0, 0, 0
    model.train()
    checkpoints = []
    try:
        initial_validation = validation_loss(model, dev, micro, tokenizer.eos_token_id)
        log.write(json.dumps({"event": "validation", "epoch": 0, "step": 0, "loss": initial_validation, "examples_seen": 0}) + "\n")
        print(f"Initial held-out completion loss: {initial_validation:.4f}", flush=True)
        for epoch in range(1, config["epochs"] + 1):
            order = list(train)
            random.Random(config["seed"] + epoch).shuffle(order)
            for offset in range(0, len(order), effective):
                examples = order[offset:offset + effective]
                batches = [collate(examples[index:index + micro], tokenizer.eos_token_id) for index in range(0, len(examples), micro)]
                token_counts = [int(batch["labels"][:, 1:].ne(-100).sum()) for batch in batches]
                denominator = sum(token_counts)
                optimizer.zero_grad(set_to_none=True)
                mean_loss = 0.0
                for batch, count in zip(batches, token_counts, strict=True):
                    with torch.autocast("cuda", dtype=torch.float16):
                        loss = model(**batch).loss
                    if not torch.isfinite(loss):
                        raise RuntimeError("Non-finite training loss")
                    mean_loss += float(loss.detach()) * count / denominator
                    scaler.scale(loss * (count / denominator)).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(parameters, config["max_grad_norm"])
                previous_scale = scaler.get_scale()
                scaler.step(optimizer)
                scaler.update()
                if scaler.get_scale() < previous_scale:
                    skipped += 1
                else:
                    scheduler.step()
                    step += 1
                examples_seen += len(examples)
                event = {"event": "train", "epoch": epoch, "step": step, "examples_seen": examples_seen,
                         "loss": mean_loss, "learning_rate": scheduler.get_last_lr()[0], "skipped_updates": skipped,
                         "seconds": time.perf_counter() - started, "peak_pytorch_gib": torch.cuda.max_memory_allocated() / 1024**3}
                log.write(json.dumps(event) + "\n")
                if (offset // effective) % 5 == 0:
                    print(f"Epoch {epoch}/{config['epochs']} step {step}, examples {examples_seen}, loss {mean_loss:.4f}, peak {event['peak_pytorch_gib']:.2f} GiB", flush=True)
                del batches, batch, loss
            dev_loss = validation_loss(model, dev, micro, tokenizer.eos_token_id)
            checkpoint = weight_dir / f"epoch-{epoch}"
            model.save_pretrained(checkpoint, safe_serialization=True)
            tokenizer.save_pretrained(checkpoint)
            info = {"run_id": args.run_id, "epoch": epoch, "step": step, "examples_seen": examples_seen,
                    "validation_loss": dev_loss, "dataset_sha256": manifest["dataset_sha256"],
                    "base_model": config["model"], "revision": config["revision"], "config": config,
                    "adapter_sha256": hashlib.sha256((checkpoint / "adapter_model.safetensors").read_bytes()).hexdigest(),
                    "checkpoint": str(checkpoint.relative_to(ROOT))}
            write_json(checkpoint / "training-metadata.json", info)
            write_json(report_dir / f"epoch-{epoch}-metadata.json", info)
            checkpoints.append(info)
            log.write(json.dumps({"event": "validation", "epoch": epoch, "step": step, "examples_seen": examples_seen, "loss": dev_loss}) + "\n")
            print(f"Saved epoch {epoch}; held-out completion loss {dev_loss:.4f}", flush=True)
        sampled = [parameter for parameter in parameters if parameter.numel() < 100000]
        changed = any(not torch.equal(old, new.detach()) for old, new in zip(before, sampled, strict=True))
        if not changed or not step:
            raise RuntimeError("Adapter parameters did not update")
        metadata.update(status="complete", optimizer_steps=step, examples_seen=examples_seen, skipped_updates=skipped,
                        initial_validation_loss=initial_validation, checkpoints=checkpoints, adapter_weights_changed=changed,
                        training_seconds=time.perf_counter() - started, peak_pytorch_gib=torch.cuda.max_memory_allocated() / 1024**3)
    except BaseException as error:
        metadata.update(status="failed", error=f"{type(error).__name__}: {error}", optimizer_steps=step, examples_seen=examples_seen)
        raise
    finally:
        log.close()
        write_json(report_dir / "training-metadata.json", metadata)


if __name__ == "__main__":
    main()
