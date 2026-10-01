# Recorded experiments

`base-functional-baseline/` records the untouched Qwen3 Base run from 2026-10-01:

- `predictions.jsonl`: each input, exact model prompt, raw completion, and generation count/timing.
- `generation-metadata.json`: resolved model commit, decoding settings, dependency versions, GPU, and suite hash.
- `evaluation.json`: Docker image ID, suite/evaluator/prediction hashes, scores, per-family totals, and per-fixture failures.

Keep named milestone results so future training runs can be compared to a known baseline. Large model weights and transient caches belong outside Git; these small experiment records are intended to be tracked.
