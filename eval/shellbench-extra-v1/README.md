# ShellBench Extra v1

Created: 2026-10-02 (Europe/Budapest).

A separate **300-case long-term progress benchmark** for the English-to-Linux-command translator. It is outside `data/shell_translation`, outside every training/validation split, and separate from the original 112-case ShellBench v1.

## Coverage

Twenty task categories have 15 cases each: navigation, listing, directory creation, empty files, copying, moving, removal, reading, text slices, counts, grep, find, sorting/deduplication, text transformations, field extraction/aggregation, writing/redirection, permissions, symbolic links, pipelines, and conditionals.

There are 69 practical cases, 105 edge cases, and 126 composition cases. These describe intended structure, not difficulty calibrated against model scores. Requests are individually authored, with unfamiliar paths, varied wording, spaces/apostrophes, Unicode, literal dollar signs/globs/semicolons/command-substitution text, recursive exclusions, byte thresholds, exact line ranges, combined predicates, and explicit preservation requirements.

Shared Linux primitives remain the target skill domain. The cases use zero identical normalized requests or exact reference commands from existing training/validation releases or the original benchmark. The independent fixtures, explicit commands, and Python expectations are authored separately from training catalogs. This is stronger separation than random row splitting, but is not proof that every meaning or command structure is novel.

## Files and checks

- `cases.jsonl`: 300 complete request/reference/expectation records, no training `split` or `intent` fields.
- `manifest.json`: version, counts, authoring provenance, and frozen case fingerprint.
- `validation.json`: successful two-fixture reference verification, image/code/fixture fingerprints, separation audit, and existing data-shard hashes.
- `validation-initial-worker.json`: archived reference validation before the restrictive-permissions worker repair; current measurements use `validation.json`.
- `shellbench/extra_fixtures.py`: two new deterministic filesystem worlds, with decoys, preserved sentinels, differing contents/counts, a threshold-boundary file, and a conditional gate present in only one world.
- `shellbench/extra_oracle.py`: independent expected stdout, final working directory, and filesystem effects. It evaluates structured expectations in Python and never parses reference commands to manufacture answers.

`expectation` contains `cwd`, `stdout` expressions, and `effects`. For example, a size-and-extension search defines the desired file selection; a move defines its source/destination state changes. The reference is separately written shell code. The model sees only the English request in the normal request/command prompt.

All 300 references passed two fixtures: **600 reference executions**. Candidate commands run in the existing disposable Docker sandbox and must pass both worlds. Comparisons check Bash syntax, exit status, stderr, stdout, final cwd, and all observed files/directories/symlinks under `/workspace` and home, including contents and permissions. Wrong operations and collateral changes fail even when output looks right.

The worker records original permissions even for unreadable files/directories, temporarily restoring read/traversal access for observation and restoring modes afterward. Directory access is restored before fixture cleanup. This fixes an infrastructure failure discovered during the first epoch-2 measurement; earlier partial-run reports remain archived, and final comparisons all use the corrected worker.

Exact command matching is diagnostic. `lines` mode permits result order differences when ordering is not requested. `number` mode permits whitespace around a numeric count while rejecting extra filename labels. Ordered outputs remain strict. No confidence interval or broad real-world reliability claim is implied by the aggregate percentage.

## Run it explicitly

From the repository root in WSL, with the existing environment and Docker Desktop running:

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv run python -m shellbench build
uv run python -m shellbench validate --suite shellbench-extra-v1
uv run python -m shellbench generate \
  --suite shellbench-extra-v1 \
  --revision da87bfb608c14b7cf20ba1ce41287e8de496c0cd \
  --adapter checkpoints/2026-10-01-lora-pilot-v1/epoch-3 \
  --batch-size 8 \
  --output reports/my-extra-measurement/epoch-3
uv run python -m shellbench evaluate \
  --suite shellbench-extra-v1 \
  --predictions reports/my-extra-measurement/epoch-3/predictions.jsonl
```

Omit `--adapter` to measure Base. An explicit helper measures Base and all saved epochs of a completed run:

```bash
uv run python tools/evaluate_extra.py \
  --training-run 2026-10-01-lora-pilot-v1 \
  --report-id my-extra-comparison
```

Rebuild the image after worker changes. The helper can continue matching saved predictions/results and rejects stale evaluator/image fingerprints; use a fresh report ID for another snapshot. Preserve earlier reports.

Export charts for the completed initial comparison with Matplotlib available:

```bash
uv run --with matplotlib python tools/plot_extra.py \
  --report-id 2026-10-02-shellbench-extra-v1
```

The chart command creates PNG/SVG exports and a source CSV under the report's `charts/` directory. It keeps original ShellBench and Extra as separate series.

Greedy decoding retains the original raw prompt, EOS/newline stopping, pinned base revision, and 64-token cap. All reference commands fit the cap (the longest is 42 tokens including EOS). The initial Extra measurements use batches of eight; a real Qwen check on four unequal-length requests matched serial outputs exactly. Batch setting and amortized timing are recorded; these runs are not controlled inference performance benchmarks.

## Use protocol

Develop primarily using the training/validation splits. Choose training settings and checkpoints using development validation signals. Keep Extra for occasional, completed-milestone snapshots of the desired broader outcome; do not adapt training examples directly from its prompts or reference commands. The default trainer and existing checkpoint evaluation helper do not invoke Extra.

The initial run retrospectively measures all three already-trained adapters to establish the historical curve. Those adapters were trained before Extra was authored; no retraining or checkpoint optimization occurs here.

Preserve v1 requests and expectations. Changes require a new suite version, not rewriting past charts. Plot original ShellBench and Extra as separate series with their own case counts. A future untouched final test remains useful: if Extra is used to guide repeated case-specific tuning, its role becomes development feedback. Exact leakage guards cannot detect all semantic paraphrases or equivalent command spellings.

The scope assumes GNU/Linux tools, Bash, a fixed C locale, and controlled local files. It excludes network/root administration, interactive programs, timestamps/ownership, and underspecified requests requiring a clarification response. No new uncertainty-response protocol is imposed on the command-only model.

See [the implementation and results notebook](../../docs/shellbench-extra-v1.md).
