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
