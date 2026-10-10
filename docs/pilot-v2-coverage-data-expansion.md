# Pilot v2: coverage-driven training data expansion

Date: 2026-10-10 (Europe/Budapest).

## Purpose and status

Prepare a substantially larger, reviewable English-to-shell dataset before the next fresh LoRA experiment. The user requested data first, followed by approval before training. **No training or model generation was run in this milestone.**

The previous expanded-data adapter achieved 95/112 (84.8%) functional accuracy on ShellBench v1. Its 17 failures highlighted broad weaknesses in quoting, interpreting paths, file-operation intent, search options, and combinations of filesystem filters. We used these capability categories to design new scenarios. Benchmark prompts were not paraphrase sources. Neither benchmark's cases or reference commands were edited.

ShellBench v1 is a development diagnostic after this analysis. ShellBench Extra v1 stays separate from the training/validation release and was used only by overlap/exclusion audits during this work. Exact overlap guards do not establish semantic independence; reserve a future blinded test before making final generalization claims.

## Dataset contents

`pilot-v2` is a complete snapshot containing all of the current `pilot-v1` data plus the expansion. Future training should load **pilot-v2 alone**, rather than loading both releases and duplicating the inherited examples.

| Property | Inherited | Added | Complete pilot-v2 |
| --- | ---: | ---: | ---: |
| Examples | 2,444 | 20,340 | 22,784 |
| Training | 2,072 | 16,320 | 18,392 |
| Validation | 372 | 4,020 | 4,392 |
| Scenario groups | 611 | 3,390 | 4,001 |

The complete release contains 74 command families and 3,959 distinct command strings. Fourteen families receive new examples: `cd`, `ls`, `mkdir`, `touch`, `cp`, `mv`, `rm`, `cat`, `head`, `tail`, `wc`, `grep`, `find`, and `chmod`. The less common utility families remain present through the inherited data. Expansion intentionally weights the core translator capabilities more heavily; there is no claim that the resulting distribution is balanced across all 74 families.

Each new scenario has six authored English forms. They use different sentence structures and preserve the same explicit constraints. Literal arguments cover ordinary names, spaces, apostrophes, leading dashes, dollar signs, semicolons, asterisks, brackets, and accented characters. The literal characters must survive shell quoting; they are not instructions to expand variables, glob filenames, or execute additional commands.

### Added capabilities

- Relative, dot-relative, parent-relative and absolute navigation; filesystem root versus user home versus parent versus current folder.
- Immediate directory listings versus recursive searches; hidden entries, long listings, and one entry per line.
- One or multiple new files/directories; files inside an existing folder; missing directory parents; explicit final-directory permissions.
- Copy versus move, destination file versus existing destination directory, multiple sources, and recursive directory transfers.
- Read-only concatenation versus overwrite versus append, including source order and preservation of existing destination text.
- Beginning versus end of a file, a single line versus several lines, bytes versus lines, and line/word/byte counts.
- Literal text search, case handling, inversion, line numbers, matching-line counts, and recursively returning filenames based on file contents.
- File versus directory search, extension filters, empty entries, depth limits, strict byte thresholds, and combinations of filters.
- File permissions versus directory-only permissions versus a whole recursive tree.

This milestone does not introduce a general pipeline grammar, arbitrary regular expressions, timestamp searches, process/network administration, or every Linux tool. Those need separate observable intent contracts and data work.

## Layout and contributor workflow

```text
data/shell_translation/
  catalogs/pilot-v2/<topic>/<family>.json       # editable scenario groups
  releases/pilot-v2/families/<topic>/*.jsonl    # complete rendered examples
  releases/pilot-v2/manifest.json              # counts and content hashes
  releases/pilot-v2/validation.json            # Docker execution validation
  authoring/pilot-v2/coverage.json             # parent, matrix and capability counts
  authoring/pilot-v2/quality.json              # separation and tokenizer audit
  authoring/pilot-v2/tests.json                # regression commands and exit statuses
  authoring/pilot-v2/review.md                 # commands and paraphrases to review
```

`tools/build_coverage_catalog.py` records the authored scenario matrix, vocabulary pools and sentence banks. It reads editable parent catalogs, checks labels and overlap, and writes the new catalogs. It refuses to regenerate over a rendered release. The catalogs and full JSONL are committed source artifacts; training needs no API calls or on-the-fly synthetic generation. Contributors can edit a future copied catalog release without changing the trainer.

All 611 parent groups retain their original IDs, requests, intents and splits. Their source paths and release provenance correctly identify the new snapshot. Existing `pilot-v1` catalogs, rendered data, validation record and archived model results are preserved.

The authoring review pack samples two scenarios per capability/split where available, showing all six requests, the structured intent and command. It is a practical review aid, not a claim that every English sentence has had independent human review.

## Splits and separation

The new matrix uses 40 training argument roots and 10 separate validation argument roots. All paraphrases of a scenario stay together. Validation has six separate sentence forms per task, distinct from the corresponding training bank. New validation command labels do not occur in training, including the inherited training examples. Small primitive navigation and current-location scenarios are training-only.

New validation therefore measures argument and phrasing generalization together. It **does not isolate composition generalization**: both splits contain the same supported combinations with different arguments and wording. Inherited validation keeps its previous, weaker rules. Report old and new validation cohorts separately when interpreting the next experiment. A future composition holdout should be explicitly designed before its results are used to steer training.

The compiler rejects normalized duplicate requests, benchmark-request overlap, Extra v1 exact reference labels, invalid fields, inconsistent group splits and incorrect rendered labels. The quality audit additionally checks the parent snapshot, the authoring matrix, new label split separation, vocabulary separation, sentence skeletons, the frozen Extra suite and all tokenizer boundaries.

## Functional checks and infrastructure changes

`shellm_data/intents.py` now supports `cat` with optional `output` and `append`. Appending requires an output, and a destination that resolves to a source is rejected. Source order, destination contents, stdout and filesystem effects are modeled independently of the command renderer. Output fixtures begin with existing text so overwrite and append cannot accidentally pass the same check.

Search fixtures now include files at the exact byte threshold and just above it, deeper matches, mismatched extensions, empty and occupied directories, and symlinks. This makes omitted size/depth/type/empty filters observable. The empty-directory oracle checks descendants instead of expecting a file-size attribute. Recursive content-search output preserves the requested path prefix, including `./`. Default text fixtures use ASCII content while filenames can remain Unicode, allowing deterministic byte slicing without invalid UTF-8 boundaries.

`tests/test_coverage_data.py` checks the preserved parent, reproducible compilation, split integrity and invalid redirection intents. Its Docker contrasts accept equivalent commands and reject wrong quoting, missing options, wrong size boundaries, wrong file order, unexpected writes and overwrite/append confusion. Two fixtures are used for each contrast.

These changes affect training-label validation only; the frozen benchmark fixtures/oracles were not changed. The old `pilot-v1/validation.json` remains a historical record of the previous validator. Revalidate that release explicitly before a future training run requiring the current validator hash. Pilot v2 receives its own full validation under the current code.

## Commands

Run in WSL from the repository root:

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"

# Author/build only when creating an unpublished release:
uv run python tools/build_coverage_catalog.py
uv run python -m shellm_data build --release pilot-v2

# Reproduce checks for the committed release:
uv run python -m shellm_data build --release pilot-v2 --check
uv run python tools/lint_requests.py --release pilot-v2 --all --group-prefix coverage-v2-
uv run python -m unittest tests.test_coverage_data tests.test_training_data tests.test_chmod_intent
uv run python -m shellm_data validate --release pilot-v2
uv run python tools/audit_coverage_release.py
```

The linter's new `--group-prefix` selector checks every added group, including the original command families normally skipped by default. Its skeleton comparisons still include inherited scenarios. It does not retroactively claim that all inherited paraphrases satisfy the newer linter.

## Observed results

- All **4,001 scenarios passed both independent Docker fixtures: 8,002 label executions**. Checks cover syntax, exit status, stdout/stderr, working directory and observable filesystem state against typed-intent expectations.
- Dataset SHA-256: `d546e6075d539854706eecce78ce0e3667257c067a218722945ddff545265e93`.
- Docker image: `sha256:66da86ce8a79e4847adee80e063b5bea9e9d4b1d457caec2c62084d9055a4068`.
- No requests overlap either reserved benchmark after normalization. Both suites' case files remain unchanged.
- The stricter request linter passed **all 3,390 new groups**. No added command labels cross training/validation, and the new argument pools and sentence skeletons have zero split overlap. All 611 inherited groups and the checked authoring matrix reproduce exactly.
- All **22,784 examples** passed the pinned Qwen Base tokenizer's prompt/completion boundary, loss-mask and EOS checks. The longest is **86 tokens**, below the existing 128-token training limit; no truncation was needed. The complete dataset contains 943,078 tokens, including 329,190 supervised completion/EOS tokens (both splits combined).
- Tokenizer and separation audit details are preserved in `authoring/pilot-v2/quality.json`; functional execution results are in `releases/pilot-v2/validation.json`.
- **22 regression tests passed**: four new release/contrast tests and eighteen existing dataset/chmod tests. Commands and verified exit statuses are preserved in `authoring/pilot-v2/tests.json`. Temporary WSL logs were ephemeral; there is no archived raw-log claim.

## Limits and next step

This is authored, template-based synthetic data. Twenty thousand examples are not twenty thousand independent linguistic structures. Executing a label against an intent oracle validates command behavior in the fixtures, not the meaning of every English paraphrase. The inherited utility families retain their documented oracle limitations, including timing and some identity/link observations. The new split checks do not repair the inherited split design.

No improvement in model accuracy has been measured from this release. Next step: the user reviews the concrete dataset and approves it, then explicitly requests a fresh LoRA run. Select training settings and compare the model using internal validation and both preserved benchmarks in that later milestone.
