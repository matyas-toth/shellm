"""Generate and functionally score each saved epoch without replacing older results."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(*arguments):
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id):
        raise SystemExit("Invalid run ID")
    report = ROOT / "reports" / args.run_id
    training = json.loads((report / "training-metadata.json").read_text())
    if training["status"] != "complete":
        raise SystemExit("Wait for the training run to complete before checkpoint evaluation")
    for checkpoint in training["checkpoints"]:
        adapter = ROOT / checkpoint["checkpoint"]
        if hashlib.sha256((adapter / "adapter_model.safetensors").read_bytes()).hexdigest() != checkpoint["adapter_sha256"]:
            raise SystemExit(f"Checkpoint fingerprint mismatch: {adapter}")
        directory = report / "evaluations" / f"epoch-{checkpoint['epoch']}"
        if not directory.exists():
            run("-m", "shellbench", "generate", "--model", training["config"]["model"],
                "--revision", training["config"]["revision"], "--adapter", str(adapter), "--output", str(directory))
        else:
            generation = json.loads((directory / "generation-metadata.json").read_text())
            if generation["adapter_sha256"] != checkpoint["adapter_sha256"]:
                raise SystemExit(f"Existing predictions use a different adapter: {directory}")
        if not (directory / "evaluation.json").exists():
            run("-m", "shellbench", "evaluate", "--predictions", str(directory / "predictions.jsonl"))
        summary = json.loads((directory / "evaluation.json").read_text())["summary"]
        print(f"Epoch {checkpoint['epoch']}: {summary['functional_ok']}/{summary['total']} functional", flush=True)
    run("tools/report_history.py")


if __name__ == "__main__":
    main()
