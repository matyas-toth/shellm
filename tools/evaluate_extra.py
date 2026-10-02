"""Explicit milestone-only Extra measurement of a completed run and its frozen base."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-run", default="2026-10-01-lora-pilot-v1")
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--batch-size", type=int, choices=(1, 2, 4, 8, 16), default=8)
    args = parser.parse_args()
    for value in (args.training_run, args.report_id):
        if not value or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in value):
            raise SystemExit("Invalid run/report ID")
    training = json.loads((ROOT / "reports" / args.training_run / "training-metadata.json").read_text())
    if training["status"] != "complete":
        raise SystemExit("Extra is measured after a completed training milestone")
    run("-m", "shellbench", "validate", "--suite", "shellbench-extra-v1")
    validation = json.loads((ROOT / "eval" / "shellbench-extra-v1" / "validation.json").read_text())
    checkpoints = [{"epoch": 0}, *training["checkpoints"]]
    for checkpoint in checkpoints:
        epoch = checkpoint["epoch"]
        adapter = ROOT / checkpoint["checkpoint"] if epoch else None
        if adapter and hashlib.sha256((adapter / "adapter_model.safetensors").read_bytes()).hexdigest() != checkpoint["adapter_sha256"]:
            raise SystemExit("Adapter fingerprint mismatch")
        directory = ROOT / "reports" / args.report_id / (f"epoch-{epoch}" if epoch else "baseline")
        command = ["-m", "shellbench", "generate", "--suite", "shellbench-extra-v1", "--model", training["config"]["model"],
                   "--revision", training["config"]["revision"], "--batch-size", str(args.batch_size), "--output", str(directory)]
        if adapter:
            command += ["--adapter", str(adapter)]
        if not directory.exists():
            run(*command)
        else:
            metadata = json.loads((directory / "generation-metadata.json").read_text())
            if (metadata.get("suite") != "shellbench-extra-v1"
                    or metadata.get("suite_sha256") != validation["suite_sha256"]
                    or metadata.get("adapter_sha256") != checkpoint.get("adapter_sha256")
                    or metadata["batch_size"] != args.batch_size
                    or metadata["model"] != training["config"]["model"]
                    or metadata["revision"] != training["config"]["revision"]):
                raise SystemExit("Existing predictions belong to a different comparison")
        if not (directory / "evaluation.json").exists():
            run("-m", "shellbench", "evaluate", "--suite", "shellbench-extra-v1", "--predictions", str(directory / "predictions.jsonl"))
        evaluation = json.loads((directory / "evaluation.json").read_text())
        if (evaluation.get("suite") != "shellbench-extra-v1"
                or any(evaluation[key] != validation[key] for key in ("suite_sha256", "evaluator_sha256", "image_id"))
                or evaluation["predictions_sha256"] != hashlib.sha256((directory / "predictions.jsonl").read_bytes()).hexdigest()):
            raise SystemExit("Existing scores use a different evaluator/image or predictions; choose a fresh report ID")
        summary = evaluation["summary"]
        print(f"Extra {'Base' if not epoch else 'epoch ' + str(epoch)}: {summary['functional_ok']}/{summary['total']}", flush=True)
    run("tools/report_history.py")


if __name__ == "__main__":
    main()
