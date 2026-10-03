"""Compare one completed LoRA checkpoint with its frozen Base on both benchmarks."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shellbench.sandbox import docker_cli, image_id
from shellbench.suites import SUITES, evaluator_digest, suite_path


def run(*arguments):
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--epoch", type=int, help="Defaults to the final saved epoch")
    parser.add_argument("--batch-size", type=int, choices=(1, 2, 4, 8, 16), default=8)
    args = parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id):
        raise SystemExit("Invalid run ID")
    report = ROOT / "reports" / args.run_id
    training = json.loads((report / "training-metadata.json").read_text())
    if training["status"] != "complete":
        raise SystemExit("Wait for training to complete before running the milestone comparison")
    epoch = args.epoch if args.epoch is not None else max(c["epoch"] for c in training["checkpoints"])
    checkpoint = next(c for c in training["checkpoints"] if c["epoch"] == epoch)
    adapter = ROOT / checkpoint["checkpoint"]
    if sha(adapter / "adapter_model.safetensors") != checkpoint["adapter_sha256"]:
        raise SystemExit("Adapter fingerprint mismatch")
    config = training["config"]
    image = image_id(docker_cli())
    for suite in SUITES:
        run("-m", "shellbench", "validate", "--suite", suite)
        suite_hash = sha(suite_path(suite))
        for name, selected in (("baseline", None), (f"epoch-{epoch}", adapter)):
            directory = report / "benchmarks" / suite / name
            if not directory.exists():
                command = ["-m", "shellbench", "generate", "--suite", suite,
                           "--model", config["model"], "--revision", config["revision"],
                           "--batch-size", str(args.batch_size), "--output", str(directory)]
                if selected:
                    command += ["--adapter", str(selected)]
                run(*command)
            generation = json.loads((directory / "generation-metadata.json").read_text())
            expected = {"suite": suite, "suite_sha256": suite_hash, "model": config["model"],
                        "revision": config["revision"], "batch_size": args.batch_size,
                        "do_sample": False, "max_new_tokens": 64, "prompt_style": "raw",
                        "adapter_sha256": checkpoint["adapter_sha256"] if selected else None}
            if any(generation.get(key) != value for key, value in expected.items()):
                raise SystemExit(f"Existing predictions use different settings: {directory}")
            if not (directory / "evaluation.json").exists():
                run("-m", "shellbench", "evaluate", "--suite", suite,
                    "--predictions", str(directory / "predictions.jsonl"))
            evaluation = json.loads((directory / "evaluation.json").read_text())
            expected = {"suite": suite, "suite_sha256": suite_hash, "image_id": image,
                        "evaluator_sha256": evaluator_digest(suite),
                        "predictions_sha256": sha(directory / "predictions.jsonl")}
            if any(evaluation.get(key) != value for key, value in expected.items()):
                raise SystemExit(f"Existing scores use a different evaluator/image/predictions: {directory}")
            summary = evaluation["summary"]
            print(f"{suite} {name}: {summary['functional_ok']}/{summary['total']} "
                  f"({100 * summary['functional_ok'] / summary['total']:.1f}%)", flush=True)
    run("tools/report_history.py")


if __name__ == "__main__":
    main()
