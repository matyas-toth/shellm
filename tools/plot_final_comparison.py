"""Plot one trained checkpoint against its matched Base on both frozen benchmarks."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS = (("shellbench-v1", "ShellBench v1"), ("shellbench-extra-v1", "ShellBench Extra v1"))
COLORS = ("#aab7c2", "#146b80")


def load_rows(report, epoch):
    rows = []
    for suite, label in BENCHMARKS:
        identity = None
        for model, name in (("Qwen3 0.6B Base", "baseline"), ("Fresh SheLLM LoRA", f"epoch-{epoch}")):
            directory = report / "benchmarks" / suite / name
            source = directory / "evaluation.json"
            result = json.loads(source.read_text())
            generation = json.loads((directory / "generation-metadata.json").read_text())
            fingerprint = (result["suite_sha256"], result["evaluator_sha256"], result["image_id"],
                           generation["model"], generation["revision"], generation["batch_size"],
                           generation["prompt_style"], generation["do_sample"], generation["max_new_tokens"],
                           tuple(generation["stop_strings"]), generation["dtype"])
            if result["suite"] != suite or generation["suite"] != suite or identity and identity != fingerprint:
                raise ValueError("Model comparison must share benchmark/evaluator/image/decoding settings")
            identity = fingerprint
            if hashlib.sha256((directory / "predictions.jsonl").read_bytes()).hexdigest() != result["predictions_sha256"]:
                raise ValueError("Archived predictions changed")
            summary = result["summary"]
            rows.append({"suite": suite, "benchmark": label, "model": model,
                         "epoch": 0 if name == "baseline" else epoch,
                         "correct": summary["functional_ok"], "total": summary["total"],
                         "percent": 100 * summary["functional_ok"] / summary["total"],
                         "report": source.relative_to(ROOT).as_posix(),
                         "adapter_sha256": generation.get("adapter_sha256", "")})
    return rows


def axes_style(ax):
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
    ax.set_ylabel("Functional accuracy", labelpad=12, color="#5c6b77")
    ax.grid(axis="y", color="#e8edf0", zorder=0)
    ax.tick_params(axis="both", length=0, pad=10, colors="#5c6b77")
    for spine in ax.spines.values():
        spine.set_visible(False)


def annotate(ax, bars, rows):
    for bar, row in zip(bars, rows, strict=True):
        x, y = bar.get_x() + bar.get_width() / 2, bar.get_height()
        ax.text(x, y + 2.5, f"{row['percent']:.1f}%", ha="center", fontsize=18,
                weight="bold", color="#172b3a")
        ax.text(x, max(3, y - 6), f"{row['correct']} / {row['total']}", ha="center", fontsize=11,
                color="#263b4b" if row["epoch"] == 0 else "white")


def save(fig, output, name):
    for extension in ("png", "svg"):
        fig.savefig(output / f"{name}.{extension}", facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--epoch", type=int, help="Defaults to final saved epoch")
    args = parser.parse_args()
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id):
        raise SystemExit("Invalid run ID")
    report = ROOT / "reports" / args.run_id
    training = json.loads((report / "training-metadata.json").read_text())
    epoch = args.epoch if args.epoch is not None else max(c["epoch"] for c in training["checkpoints"])
    rows = load_rows(report, epoch)
    checkpoint = next(c for c in training["checkpoints"] if c["epoch"] == epoch)
    if any(row["epoch"] and row["adapter_sha256"] != checkpoint["adapter_sha256"] for row in rows):
        raise ValueError("Plotted model differs from the saved training checkpoint")
    output = report / "charts"
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "svg.fonttype": "none"})
    footer = f"Fresh LoRA · {training['train_examples']:,} training examples · checkpoint epoch {epoch} · both fixtures required"
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=160)
    fig.subplots_adjust(left=0.105, right=0.96, bottom=0.19, top=0.76)
    fig.text(0.105, 0.92, "Fresh LoRA vs Qwen3 Base", fontsize=24, weight="bold", color="#172b3a")
    fig.text(0.105, 0.865, "csanad-shenanigans · expanded-data experiment · 0.6B models", fontsize=12, color="#5c6b77")
    axes_style(ax)
    ax.set_xticks([0, 1], ["ShellBench v1\n112 cases", "ShellBench Extra v1\n300 cases"])
    for index, (model, color) in enumerate(zip(("Qwen3 0.6B Base", "Fresh SheLLM LoRA"), COLORS)):
        subset = [row for row in rows if row["model"] == model]
        bars = ax.bar([i + (-0.18 if index == 0 else 0.18) for i in range(2)],
                      [row["percent"] for row in subset], width=0.32, color=color, label=model, zorder=3)
        annotate(ax, bars, subset)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.96, 0.825),
               ncol=2, frameon=False, fontsize=11)
    fig.text(0.105, 0.083, footer, fontsize=10, color="#5c6b77")
    fig.text(0.105, 0.045, "Different benchmark coverage; each Base/LoRA pair shares the same evaluation settings.", fontsize=10, color="#5c6b77")
    save(fig, output, "final-model-versus-base-both-benchmarks")

    for suite, label in BENCHMARKS:
        subset = [row for row in rows if row["suite"] == suite]
        fig, ax = plt.subplots(figsize=(9, 6.5), dpi=160)
        fig.subplots_adjust(left=0.12, right=0.96, bottom=0.19, top=0.76)
        fig.text(0.12, 0.92, label, fontsize=24, weight="bold", color="#172b3a")
        fig.text(0.12, 0.865, "Qwen3 0.6B Base and fresh expanded-data LoRA", fontsize=12, color="#5c6b77")
        axes_style(ax)
        ax.set_xticks([0, 1], ["Qwen3 Base", "Fresh SheLLM LoRA"])
        bars = ax.bar([0, 1], [row["percent"] for row in subset], width=0.55, color=COLORS, zorder=3)
        annotate(ax, bars, subset)
        fig.text(0.12, 0.083, footer, fontsize=9, color="#5c6b77")
        fig.text(0.12, 0.045, "Held-out functional evaluation · output, exit status, cwd, and filesystem effects checked", fontsize=9, color="#5c6b77")
        save(fig, output, f"{suite}-final-versus-base")
    with (output / "comparison.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved final-checkpoint comparison PNG/SVG charts and CSV to {output}")


if __name__ == "__main__":
    main()
