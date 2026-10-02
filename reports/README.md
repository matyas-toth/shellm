# Recorded experiments

`base-functional-baseline/` records the untouched Qwen3 Base run from 2026-10-01:

- `predictions.jsonl`: each input, exact model prompt, raw completion, and generation count/timing.
- `generation-metadata.json`: resolved model commit, decoding settings, dependency versions, GPU, and suite hash.
- `evaluation.json`: Docker image ID, suite/evaluator/prediction hashes, scores, per-family totals, and per-fixture failures.

Keep named milestone results so future training runs can be compared to a known baseline. Large model weights and transient caches belong outside Git; these small experiment records are intended to be tracked.

LoRA experiments use `reports/<run-id>/` with training metadata, per-step JSONL logs, epoch checkpoint metadata, and `evaluations/epoch-N/` predictions/settings/functional scores. A `baseline/` replay can establish comparison with the current evaluator without replacing the original baseline.

Generate the chart index with `uv run python tools/report_history.py`. `history.csv` includes scores, epoch/step/examples seen, and model/data/evaluator fingerprints. It is regenerated from the archived JSON reports. See [the report history guide](../docs/experiment-report-history.md) for comparison rules and the full layout.

Use a fresh run ID for each experiment. Training, prediction generation, and scoring refuse to replace historical results. Keep completed logs and reports in Git; keep checkpoints in the ignored `checkpoints/` directory.

Extra measurements use a separate report ID, such as `2026-10-02-shellbench-extra-v1/`, with `baseline/` and `epoch-N/` subdirectories. Each retains raw predictions, generation metadata, and evaluation results tagged with `shellbench-extra-v1`. History CSV includes suite and benchmark-run fields. Keep benchmark series separate; old 112-case scores and new 300-case scores measure different request distributions.

The initial Extra run also preserves two `evaluation-initial-worker.json` archives from before the restrictive-permissions worker repair. Current `evaluation.json` files all use the corrected worker/image. The history exporter indexes those current files; the initial partial-run archives are retained for provenance and are not plotted as additional training improvements. Exported charts and source CSV live in the benchmark report's `charts/` folder.
