# Experiment history and future charts

Date: 2026-10-01 (Europe/Budapest).

## Storage contract

Every training experiment uses a fresh run ID under `reports/<run-id>/`. The training configuration, dataset fingerprint, installed packages, GPU, precision, seed, trainable parameter count, and final status live in `training-metadata.json`. `training-log.jsonl` contains every optimizer-attempt loss/rate/time/memory record plus validation loss before training and after each epoch. Epoch metadata links each checkpoint to its adapter hash, optimizer step, and number of examples seen.

```text
reports/<run-id>/
  training-metadata.json
  training-log.jsonl
  epoch-1-metadata.json
  epoch-2-metadata.json
  epoch-3-metadata.json
  evaluations/
    baseline/{predictions.jsonl,generation-metadata.json,evaluation.json}
    epoch-1/{predictions.jsonl,generation-metadata.json,evaluation.json}
    epoch-2/{predictions.jsonl,generation-metadata.json,evaluation.json}
    epoch-3/{predictions.jsonl,generation-metadata.json,evaluation.json}
```

`predictions.jsonl` preserves raw completions and generation counts/times. `evaluation.json` preserves aggregate, per-family, and per-case functional outcomes. Generation metadata embeds the checkpoint training metadata, enabling plots against epoch, optimizer steps, or examples seen. Checkpoints belong in ignored `checkpoints/<run-id>/epoch-N/`; their fingerprints and small metadata stay in Git.

During a running experiment, its status metadata and log evolve. After completion, preserve them. Training refuses an existing run ID, generation refuses an existing prediction directory, and evaluation refuses an existing result file. Failed runs retain failure metadata for review; use a fresh run ID for another attempt. No automatic training resume or optimizer-state checkpointing is implemented in this pilot.

## Build a chart index

```bash
uv run python tools/report_history.py
```

This regenerates `reports/history.csv` from archived `evaluation.json` files and their adjacent generation metadata. It exports functional counts/rates, exact match, format/syntax counts, epoch/step/examples seen, validation loss, base revision, adapter/dataset fingerprints, suite/evaluator fingerprints, image ID, and source report paths. CSV is a convenience index; the original JSON reports are authoritative.

Compare runs with the same evaluation suite, intended scoring behavior, prompt, and decoding settings. A different suite hash can mean either a changed request set or changed comparison annotations; investigate before connecting points in a chart. The old Base generation hash predates a correction to two long-listing comparison tags. The requests stayed identical, and the old predictions were rescored. History exports both suite hashes and a mismatch indicator rather than concealing this change.

The LoRA milestone includes a separate Base replay through the current evaluator/image. It does not represent another model training improvement. Avoid counting the original and replayed Base score as two independent observations. Training loss is token prediction cross-entropy on command completions; functional accuracy is success on two filesystem fixtures. Plot them separately.

## Evaluate saved epochs

```bash
uv run python tools/evaluate_checkpoints.py --run-id <completed-run-id>
```

The script checks the completed training record and saved adapter hashes, generates predictions for each saved epoch, runs functional evaluation, and updates the history index. It can continue if earlier epochs already have matching predictions/results; it never replaces those files.

These reports make later learning curves possible. They do not yet establish a broad shell-command benchmark or controlled inference throughput measurements.

## Separate benchmark snapshots — 2026-10-02

ShellBench Extra v1 adds an explicit periodic measurement of completed runs. Use `tools/evaluate_extra.py --training-run <completed-run-id> --report-id <fresh-report-id>`; the ordinary training and checkpoint evaluation commands retain their existing defaults. Extra predictions and evaluations are stored under `reports/<fresh-report-id>/{baseline,epoch-1,epoch-2,epoch-3}/` with embedded training/checkpoint metadata.

The history CSV now exports `suite` and `benchmark_run` alongside the existing fingerprints. Keep ShellBench v1 and Extra v1 as separate chart series: their case counts and capability distributions differ. The initial Extra charts include their source CSV and leave the original pilot reports intact. All new Extra measurements use batch size eight; per-request generation times are amortized batch times and should not be compared with the old serial measurements as throughput results.

Primary development and checkpoint choices remain based on training validation splits. Extra is a milestone progress gauge. See [ShellBench Extra v1](shellbench-extra-v1.md) for construction, verification, initial scores, and remaining limitations.
