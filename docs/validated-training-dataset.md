# First validated training dataset

Completed: 2026-10-01 (Europe/Budapest).

## What we built

The pilot release contains **1,008 training examples and 112 validation examples**, balanced across the existing 14 command families. Every scenario has four authored paraphrases. There are 280 intent groups and 261 distinct command strings. Files are stored under `data/shell_translation/` in topic/family directories, with source catalogs and full rendered JSONL examples as ordinary text intended for Git.

The catalog defines the intended operation, arguments, options, split, and English requests. `shellm_data/intents.py` renders a canonical Bash command, creates independent test fixtures, and checks the intended effect using Python expectations. `shellm_data/core.py` builds releases, detects duplicates and evaluation request overlap, enforces group splits, and verifies content hashes. The trainer loads any release manifest rather than hardcoding file names or families.

Pilot coverage includes directory navigation, listing flags, file creation/copy/move/removal, concatenation, text slices and counts, literal text search, and filesystem search. Examples cover spaces, apostrophes, leading-dash arguments, multiple files, directories, parent creation, permissions 700, recursive operations, and a small set of combined search conditions. Pipelines, ambiguous requests, regex tasks, and broad unfamiliar composition remain future coverage.

## Validation and separation

All 280 groups passed two fixtures each: **560 label executions**. Checks cover successful Bash execution, stderr/output limits, final working directory, filesystem paths/types/permissions/contents, and operation-specific stdout. Shared paraphrases share a validated command; we did not execute 1,120 distinct labels.

All paraphrases in a group belong to one split. The first 18 scenarios per family are training; the last two are validation. Most validation scenarios reserve the names `tundra` and `zephyr`; `pwd` holds out wording. This is a modest argument holdout with shared phrasing templates, not a strict test of novel linguistic structures or novel compositions. Identical labels such as `pwd` can naturally recur across splits.

Normalized requests have zero overlap with `eval/cases.jsonl`. The evaluation families intentionally overlap with the training taxonomy. The suite remains a development benchmark; avoiding exact prompts is not proof of semantic independence or a substitute for a blinded final test set.

## Reproducibility

Dataset content SHA-256:

```text
57653a7992e7186acbf7e6a25c496a85e335b30915dd823a2cb681ef5a5f1594
```

The release's `manifest.json` records shard hashes and counts; `validation.json` records the successful validator fingerprint and Docker image ID. `build --check` verified that all source catalogs reproduce the exact rendered release. Existing releases refuse overwrite. `tools/seed_pilot_catalog.py` retains the initial authoring recipe; JSON catalogs are now the editable source.

The Docker worker gained optional per-item fixtures for trusted training-label validation. The existing evaluation path uses its original shared fixtures. Replaying the original Base predictions on the rebuilt image still produced **30/112 functional passes**; the original report was preserved.

## Training format verification

Internally, each request uses:

```text
Request: <request>
Command: <command><EOS>
```

The loss masks all prompt tokens and padding, supervises command tokens plus EOS, and rejects examples longer than the configured limit. Real Qwen tokenizer checks verified the prompt/completion boundary and loss labels for every example. Maximum sequence length is 50 tokens, below the 128-token limit; no example was truncated.

All 20 test methods passed, including existing Docker equivalence/error checks plus new release consistency, split leakage, evaluation overlap, label integrity, shell quoting, intent type, prompt masking, EOS, and padding checks.

## Contribution workflow and limits

See [the dataset README](../data/shell_translation/README.md) and [contribution guide](training-data-contribution-guide.md). Contributors create a new release, add scenarios to existing family catalogs, compile, validate, and review the rendered diff. Adding a family requires a renderer and independent fixture/oracle support, while the trainer stays generic.

The English text uses authored phrasing templates plus argument variation. Functional validation verifies command labels on controlled fixtures; it cannot automatically prove every English paraphrase is correct. This dataset is intended to establish a training/evaluation loop. More data should follow measured failure patterns rather than simply multiplying these templates.

Next milestone within this experiment: train the first LoRA adapter and evaluate each epoch on the preserved functional suite.
