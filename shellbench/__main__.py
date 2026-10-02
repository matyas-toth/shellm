"""Usage: python -m shellbench {build,validate,generate,evaluate}."""

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time
from zoneinfo import ZoneInfo

from .sandbox import build_image, docker_cli, evaluate, image_id, load_cases, reference_results
from .suites import SUITES, evaluator_digest, suite_fixtures, suite_path


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def completed_ids(ids, tokenizer):
    """Remove batch padding after the first real EOS or newline stop."""
    ids = ids.tolist()
    for index, token in enumerate(ids, 1):
        if token == tokenizer.eos_token_id or "\n" in tokenizer.decode(ids[:index], skip_special_tokens=True):
            return ids[:index]
    return ids


def generate(args, cases):
    import torch
    from huggingface_hub import model_info
    from transformers import AutoModelForCausalLM, AutoTokenizer

    output_dir = Path(args.output) if args.output else Path("reports") / datetime.now(ZoneInfo("Europe/Budapest")).strftime("%Y-%m-%d-%H%M%S-predictions")
    if output_dir.exists():
        raise SystemExit("Prediction output directory already exists; choose a new directory to preserve history")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA unavailable")
    adapter_config = None
    if args.adapter:
        from peft import PeftConfig, PeftModel
        adapter_config = PeftConfig.from_pretrained(args.adapter)
        if adapter_config.base_model_name_or_path != args.model:
            raise SystemExit("Adapter base model does not match --model")
    requested_revision = adapter_config.revision if adapter_config and args.revision == "main" else args.revision
    revision = model_info(args.model, revision=requested_revision).sha
    if adapter_config and adapter_config.revision and adapter_config.revision != revision:
        raise SystemExit("Adapter base revision mismatch")
    print(f"Loading {args.model} at {revision}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=revision)
    tokenizer.padding_side = "left"
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, revision=revision, dtype=torch.float16).to("cuda").eval()
    if args.adapter:
        model = PeftModel.from_pretrained(model, args.adapter).eval()
    records = []
    started = time.perf_counter()
    for offset in range(0, len(cases), args.batch_size):
        batch = cases[offset:offset + args.batch_size]
        prompts = [f"Request: {case['request']}\nCommand:" for case in batch]
        inputs = tokenizer(prompts, padding=True, return_tensors="pt").to("cuda")
        step = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(**inputs, do_sample=False, max_new_tokens=64,
                                    stop_strings=["\n"], tokenizer=tokenizer, pad_token_id=tokenizer.eos_token_id)
        seconds = time.perf_counter() - step
        for row, case, prompt in zip(output, batch, prompts, strict=True):
            new_ids = completed_ids(row[inputs.input_ids.shape[-1]:], tokenizer)
            records.append({"id": case["id"], "request": case["request"], "prompt": prompt,
                            "completion": tokenizer.decode(new_ids, skip_special_tokens=True),
                            "generated_tokens": len(new_ids), "seconds": seconds / len(batch)})
        index = offset + len(batch)
        if offset // args.batch_size % 2 == 0 or index == len(cases):
            print(f"Generated {index}/{len(cases)}", flush=True)
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "predictions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    metadata = {
        "date": datetime.now(ZoneInfo("Europe/Budapest")).isoformat(), "model": args.model, "revision": revision,
        "suite": args.suite, "suite_sha256": hashlib.sha256(suite_path(args.suite).read_bytes()).hexdigest(), "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ("torch", "transformers", "huggingface-hub")},
        "gpu": torch.cuda.get_device_name(0), "dtype": "float16", "do_sample": False, "max_new_tokens": 64,
        "batch_size": args.batch_size, "padding_side": "left", "timing": "amortized batch wall time per request",
        "stop_strings": ["\n"], "prompt_style": "raw", "cases": len(cases),
        "generation_seconds": time.perf_counter() - started, "peak_pytorch_gib": torch.cuda.max_memory_allocated() / 1024**3,
    }
    if args.adapter:
        adapter = Path(args.adapter)
        metadata["adapter"] = args.adapter
        metadata["adapter_sha256"] = hashlib.sha256((adapter / "adapter_model.safetensors").read_bytes()).hexdigest()
        if (adapter / "training-metadata.json").exists():
            metadata["training"] = json.loads((adapter / "training-metadata.json").read_text())
    save_json(output_dir / "generation-metadata.json", metadata)
    print(f"Saved predictions to {output_dir}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("build")
    val = sub.add_parser("validate")
    val.add_argument("--suite", choices=SUITES, default="shellbench-v1")
    gen = sub.add_parser("generate")
    gen.add_argument("--model", default="Qwen/Qwen3-0.6B-Base")
    gen.add_argument("--revision", default="main")
    gen.add_argument("--output")
    gen.add_argument("--adapter", help="Saved LoRA adapter directory")
    gen.add_argument("--suite", choices=SUITES, default="shellbench-v1")
    gen.add_argument("--batch-size", type=int, choices=(1, 2, 4, 8, 16), default=1)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--predictions", required=True)
    ev.add_argument("--output")
    ev.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    ev.add_argument("--suite", choices=SUITES, default="shellbench-v1")
    args = parser.parse_args()
    args.suite = getattr(args, "suite", "shellbench-v1")
    cases = load_cases(suite_path(args.suite))
    if args.suite == "shellbench-extra-v1":
        from .extra_audit import audit
        audit(cases)
    if args.action == "generate":
        generate(args, cases)
        return
    if args.action == "evaluate":
        args.output = args.output or str(Path(args.predictions).parent / "evaluation.json")
        if Path(args.output).exists():
            raise SystemExit("Evaluation output already exists; choose a new file to preserve history")
    cli = docker_cli()
    if args.action == "build":
        print(build_image(cli), flush=True)
        return
    image = image_id(cli)
    fixtures = suite_fixtures(args.suite)
    if args.action == "validate":
        outcomes = reference_results(cli, image, cases, fixtures)
        print(f"Validated {len(outcomes)} references on {len(fixtures)} fixtures; all exited successfully.")
        if args.suite == "shellbench-extra-v1":
            from .extra_audit import validation_report
            save_json(suite_path(args.suite).parent / "validation.json", validation_report(cases, fixtures, image))
        return
    records = [json.loads(line) for line in Path(args.predictions).read_text(encoding="utf-8").splitlines() if line.strip()]
    predictions = {row["id"]: row for row in records}
    metadata_path = Path(args.predictions).parent / "generation-metadata.json"
    if metadata_path.exists():
        generated = json.loads(metadata_path.read_text())
        if generated.get("suite", "shellbench-v1") != args.suite:
            raise SystemExit("Predictions belong to a different benchmark suite")
        if generated.get("suite") and generated["suite_sha256"] != hashlib.sha256(suite_path(args.suite).read_bytes()).hexdigest():
            raise SystemExit("Prediction suite fingerprint mismatch; preserve historical reports and regenerate")
    if len(predictions) != len(records) or set(predictions) != {c["id"] for c in cases}:
        raise SystemExit("Predictions must contain each suite ID exactly once")
    for case in cases:
        if predictions[case["id"]].get("request") != case["request"]:
            raise SystemExit(f"Prediction request mismatch: {case['id']}")
    rows = evaluate(cli, image, cases, fixtures, predictions, args.workers)
    metrics = ("functional_ok", "format_ok", "syntax_ok", "exact_match")
    summary = {key: sum(r[key] for r in rows) for key in metrics}
    summary["usable"] = sum(r["functional_ok"] and r["format_ok"] for r in rows)
    summary["total"] = len(rows)
    by_family = {}
    for family in sorted({c["family"] for c in cases}):
        subset = [r for r in rows if r["family"] == family]
        by_family[family] = {"total": len(subset), **{key: sum(r[key] for r in subset) for key in metrics}}
    by_coverage = {}
    for coverage in sorted({c["coverage"] for c in cases}):
        ids = {c["id"] for c in cases if c["coverage"] == coverage}
        subset = [r for r in rows if r["id"] in ids]
        by_coverage[coverage] = {"total": len(subset), **{key: sum(r[key] for r in subset) for key in metrics}}
    by_difficulty = {}
    for difficulty in sorted({c.get("difficulty", "unspecified") for c in cases}):
        ids = {c["id"] for c in cases if c.get("difficulty", "unspecified") == difficulty}
        subset = [r for r in rows if r["id"] in ids]
        by_difficulty[difficulty] = {"total": len(subset), **{key: sum(r[key] for r in subset) for key in metrics}}
    failures = Counter(reason for row in rows for variant in row["fixtures"] for reason in variant["reasons"])
    save_json(args.output, {"date": datetime.now(ZoneInfo("Europe/Budapest")).isoformat(),
                           "suite": args.suite, "image_id": image, "suite_sha256": hashlib.sha256(suite_path(args.suite).read_bytes()).hexdigest(),
                           "evaluator_sha256": evaluator_digest(args.suite),
                           "predictions_sha256": hashlib.sha256(Path(args.predictions).read_bytes()).hexdigest(),
                           "fixtures": len(fixtures), "summary": summary, "by_family": by_family, "by_coverage": by_coverage, "by_difficulty": by_difficulty,
                           "failure_reasons_by_fixture": dict(failures), "cases": rows})
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
