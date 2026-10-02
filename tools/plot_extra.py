"""Plot Extra scores and a clearly separated comparison with the original benchmark."""

import argparse
import csv
import json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent.parent


def scores(report_id, original=False):
    result, fingerprint = [], None
    for epoch in range(4):
        checkpoint = f"epoch-{epoch}" if epoch else "baseline"
        path = ROOT / "reports" / report_id
        path = path / "evaluations" if original else path
        source = path / checkpoint / "evaluation.json"
        report = json.loads(source.read_text())
        identity = (report["suite_sha256"], report["evaluator_sha256"], report["image_id"])
        if fingerprint and identity != fingerprint:
            raise ValueError("Each plotted series must use the same suite/evaluator/image")
        fingerprint = identity
        if report.get("suite", "shellbench-v1") != ("shellbench-v1" if original else "shellbench-extra-v1"):
            raise ValueError("Benchmark series mismatch")
        summary = report["summary"]
        result.append({"suite": report.get("suite", "shellbench-v1"), "epoch": epoch,
                       "correct": summary["functional_ok"], "total": summary["total"],
                       "percent": summary["functional_ok"] / summary["total"] * 100,
                       "report": source.relative_to(ROOT).as_posix()})
    return result


def style(ax):
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    ax.set_xticks(range(4), ["Qwen3 Base", "SheLLM\nEpoch 1", "SheLLM\nEpoch 2", "SheLLM\nEpoch 3"])
    ax.set_ylabel("Functional accuracy", labelpad=12, color="#5c6b77")
    ax.grid(axis="y", color="#e8edf0", zorder=0)
    ax.tick_params(axis="both", length=0, pad=10, colors="#5c6b77")
    for spine in ax.spines.values():
        spine.set_visible(False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-id", default="2026-10-02-shellbench-extra-v1")
    parser.add_argument("--pilot-report", default="2026-10-01-lora-pilot-v1")
    args = parser.parse_args()
    for value in (args.report_id, args.pilot_report):
        if not value or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in value):
            raise SystemExit("Invalid report ID")
    extra, pilot = scores(args.report_id), scores(args.pilot_report, original=True)
    output = ROOT / "reports" / args.report_id / "charts"
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=160)
    fig.subplots_adjust(left=0.105, right=0.96, bottom=0.20, top=0.78)
    fig.text(0.105, 0.92, "ShellBench Extra v1", fontsize=23, weight="bold", color="#172b3a")
    fig.text(0.105, 0.865, "Long-term progress benchmark  /  300 new requests  /  0.6B models", fontsize=12, color="#5c6b77")
    style(ax)
    bars = ax.bar(range(4), [r["percent"] for r in extra], width=0.58, color=["#aab7c2", "#8bc7d1", "#4b9eae", "#146b80"], zorder=3)
    for bar, row in zip(bars, extra, strict=True):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height+3, f"{row['percent']:.1f}%", ha="center", weight="bold", fontsize=18, color="#172b3a")
        ax.text(bar.get_x() + bar.get_width()/2, max(3, height-6), f"{row['correct']} / {row['total']}", ha="center", color="white" if row["epoch"] else "#263b4b", fontsize=11)
    fig.text(0.105, 0.085, "Success required on both new filesystem fixtures. Separate from training and validation.", fontsize=10, color="#5c6b77")
    fig.text(0.105, 0.047, "Epoch 3: shellm-lora-pilot-1-epoch-3-0.6b", fontsize=10, color="#5c6b77")
    for extension in ("png", "svg"):
        fig.savefig(output / f"shellbench-extra-v1-functional-accuracy.{extension}", facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=160)
    fig.subplots_adjust(left=0.105, right=0.96, bottom=0.20, top=0.78)
    fig.text(0.105, 0.92, "Two benchmarks, separate progress measures", fontsize=21, weight="bold", color="#172b3a")
    fig.text(0.105, 0.865, "Functional accuracy  /  Qwen3 0.6B Base and the first LoRA pilot", fontsize=12, color="#5c6b77")
    style(ax)
    for shift, records, color, label in ((-0.18, pilot, "#aab7c2", "ShellBench v1 · 112 cases"), (0.18, extra, "#146b80", "Extra v1 · 300 cases")):
        bars = ax.bar([i + shift for i in range(4)], [r["percent"] for r in records], width=0.32, color=color, label=label, zorder=3)
        for bar, row in zip(bars, records, strict=True):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2.5, f"{row['percent']:.1f}%", ha="center", fontsize=11, weight="bold", color="#172b3a")
    ax.legend(loc="upper left", frameon=False, fontsize=11)
    fig.text(0.105, 0.085, "Different requests and skill coverage; each series is compared within its own frozen suite.", fontsize=10, color="#5c6b77")
    fig.text(0.105, 0.047, "Training and checkpoint decisions primarily use the development validation splits.", fontsize=10, color="#5c6b77")
    for extension in ("png", "svg"):
        fig.savefig(output / f"shellbench-v1-and-extra-v1-comparison.{extension}", facecolor="white")
    plt.close(fig)
    with (output / "comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(extra[0]))
        writer.writeheader()
        writer.writerows(pilot + extra)
    print(f"Saved comparison charts and CSV in {output}")


if __name__ == "__main__":
    main()
