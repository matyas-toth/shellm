"""Export chart-ready evaluation history from preserved report directories."""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["evaluated_at", "report", "run_id", "epoch", "optimizer_steps", "examples_seen", "total",
          "functional_correct", "functional_accuracy", "usable", "exact_match", "format_ok", "syntax_ok",
          "validation_loss", "model", "model_revision", "adapter_sha256", "dataset_sha256", "suite_sha256",
          "generation_suite_sha256", "suite_hash_match", "evaluator_sha256", "image_id", "predictions_sha256"]


def history():
    rows = []
    for source in sorted((ROOT / "reports").rglob("evaluation.json")):
        evaluation = json.loads(source.read_text())
        generation = json.loads((source.parent / "generation-metadata.json").read_text())
        training = generation.get("training", {})
        summary = evaluation["summary"]
        parts = source.relative_to(ROOT).parts
        run_id = parts[1] if len(parts) > 3 and parts[2] == "evaluations" else source.parent.name
        rows.append({"evaluated_at": evaluation["date"], "report": source.relative_to(ROOT).as_posix(),
                     "run_id": training.get("run_id", run_id), "epoch": training.get("epoch", 0),
                     "optimizer_steps": training.get("step", 0), "examples_seen": training.get("examples_seen", 0),
                     "total": summary["total"], "functional_correct": summary["functional_ok"],
                     "functional_accuracy": summary["functional_ok"] / summary["total"],
                     **{key: summary[key] for key in ("usable", "exact_match", "format_ok", "syntax_ok")},
                     "validation_loss": training.get("validation_loss", ""), "model": generation["model"],
                     "model_revision": generation["revision"], "adapter_sha256": generation.get("adapter_sha256", ""),
                     "dataset_sha256": training.get("dataset_sha256", ""),
                     "generation_suite_sha256": generation["suite_sha256"],
                     "suite_hash_match": generation["suite_sha256"] == evaluation["suite_sha256"],
                     **{key: evaluation[key] for key in ("suite_sha256", "evaluator_sha256", "image_id", "predictions_sha256")}})
    return sorted(rows, key=lambda row: (row["evaluated_at"], row["report"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/history.csv")
    args = parser.parse_args()
    rows = history()
    with Path(args.output).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} evaluations to {args.output}")


if __name__ == "__main__":
    main()
