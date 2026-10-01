"""Plot preserved ShellBench functional scores as a simple column chart."""

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="2026-10-01-lora-pilot-v1")
    args = parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id):
        raise SystemExit("Invalid run ID")
    directory = ROOT / "reports" / args.run_id
    labels = ["Qwen3 Base", "SheLLM\nEpoch 1", "SheLLM\nEpoch 2", "SheLLM\nEpoch 3"]
    names = ["qwen-3-0.6b-base"] + [f"shellm-lora-pilot-1-epoch-{epoch}-0.6b" for epoch in range(1, 4)]
    records = []
    suite, evaluator, image = None, None, None
    for name, checkpoint in zip(names, ["baseline", "epoch-1", "epoch-2", "epoch-3"], strict=True):
        path = directory / "evaluations" / checkpoint / "evaluation.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        identity = (report["suite_sha256"], report["evaluator_sha256"], report["image_id"])
        if suite is None:
            suite, evaluator, image = identity
        elif identity != (suite, evaluator, image):
            raise ValueError("Compare reports scored with the same suite, evaluator, and Docker image")
        summary = report["summary"]
        records.append({"model": name, "correct": summary["functional_ok"], "total": summary["total"],
                        "percent": 100 * summary["functional_ok"] / summary["total"],
                        "report": path.relative_to(ROOT).as_posix()})

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=160)
    fig.patch.set_facecolor("#ffffff")
    fig.subplots_adjust(left=0.105, right=0.96, bottom=0.20, top=0.78)
    fig.text(0.105, 0.92, "SheLLM vs Qwen3 Base", fontsize=23, weight="bold", color="#172b3a")
    fig.text(0.105, 0.865, "ShellBench v1  /  Functional accuracy  /  0.6B models", fontsize=12, color="#5c6b77")
    colors = ["#aab7c2", "#8bc7d1", "#4b9eae", "#146b80"]
    bars = ax.bar(range(4), [record["percent"] for record in records], width=0.58, color=colors, zorder=3)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax.set_xticks(range(4), labels, color="#263b4b", fontsize=12)
    ax.set_ylabel("Requests passed", color="#5c6b77", labelpad=12)
    ax.grid(axis="y", color="#e8edf0", linewidth=0.8, zorder=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0, pad=10, colors="#5c6b77")
    for bar, record in zip(bars, records, strict=True):
        x, height = bar.get_x() + bar.get_width() / 2, bar.get_height()
        ax.text(x, height + 3, f"{record['percent']:.1f}%", ha="center", va="bottom", fontsize=18, weight="bold", color="#172b3a")
        ax.text(x, height - 6, f"{record['correct']} / {record['total']}", ha="center", va="center", fontsize=11,
                color="#263b4b" if record == records[0] else "#ffffff")
    fig.text(0.105, 0.085, f"{records[0]['total']} requests; success required on both filesystem fixtures. Development benchmark.", fontsize=10, color="#5c6b77")
    fig.text(0.105, 0.047, "Epoch 3: shellm-lora-pilot-1-epoch-3-0.6b", fontsize=10, color="#5c6b77")
    output = directory / "charts"
    output.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(output / f"shellbench-v1-functional-accuracy.{extension}", facecolor=fig.get_facecolor())
    plt.close(fig)
    with (output / "shellbench-v1-functional-accuracy.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f"Saved PNG, SVG, and source CSV in {output}")


if __name__ == "__main__":
    main()
