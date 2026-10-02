# Contributing training examples

Date: 2026-10-01 (Europe/Budapest).

Updated: 2026-10-02 to reserve ShellBench Extra v1 requests and exact reference labels outside training/validation.

## Purpose

Make data changes reviewable, reproducible, and usable by future contributors without editing the training loop. Source catalogs, rendered examples, and validation reports all live in Git.

## Add scenarios to an existing command family

1. Copy `data/shell_translation/catalogs/pilot-v1/` to a new release directory, such as `pilot-v2/`. Published release data is preserved for experiment reproducibility.
2. Add a scenario to the appropriate topic/family JSON file. Use the seven fields shown in the dataset README: `id`, `topic`, `family`, `capability`, `split`, `intent`, and `requests`. IDs and tags use lowercase letters, digits, hyphens, or underscores.
3. Specify the intent first. Supported operation fields and types are defined in `shellm_data/intents.py` under `INTENT_FIELDS` and `validate_intent`. The family must equal `intent.op`. Unknown fields are rejected so option typos cannot silently change labels.
4. Write natural requests that describe exactly that intent. State relevant distinctions: literal versus regex search, bytes versus lines, copying versus moving, hidden entries, recursion, destination directory, and requested permissions. Review every paraphrase; the compiler cannot judge English meaning.
5. Keep all paraphrases for a scenario in the same split. Use validation examples with reserved arguments or new phrasings. Do not copy requests from `eval/cases.jsonl` or `eval/shellbench-extra-v1/cases.jsonl`, or use those suites as paraphrase sources. Extra v1 is a periodic long-term progress snapshot, outside validation; primarily develop using the validation splits. Its exact request/reference labels are guarded against reuse in future releases.
6. Compile and validate the new release, then review the JSONL diff and validation report:

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv run python -m shellm_data build --release pilot-v2
uv run python -m shellm_data validate --release pilot-v2
uv run python -m shellm_data build --release pilot-v2 --check
uv run python -m unittest discover -s tests -v
```

The compiler checks normalized request duplicates and evaluation overlap, stable IDs, group split integrity, single-line text, intent fields, and exact agreement between rendered labels and declared intents. The release manifest identifies the concrete dataset by SHA-256. The initial authoring script `tools/seed_pilot_catalog.py` is retained as provenance; contributors edit catalogs directly.

## Add a new capability or command family

Extend the intent schema and renderer, construct fixtures that distinguish correct behavior from plausible mistakes, and implement the expected output/state independently in `check_intent`. Add tests demonstrating that an equivalent command passes and a wrong command fails. Existing trainer code reads the manifest and needs no family-specific changes.

For operations such as permissions, timestamps, links, pipelines, or external programs, first extend the fixture/oracle contract as necessary. Do not declare validation successful using an oracle that cannot observe the requested effect. Training-label fixtures are independent from evaluation fixtures; the worker accepts per-scenario fixtures without changing existing evaluation cases.

## Versioning and limits

Never rewrite a dataset used by an archived experiment. Make a new release and a new training configuration/run ID. Keep source catalogs and full JSONL examples in Git. Keep large checkpoints in `checkpoints/`, which is ignored; distribute selected adapters later through a model host.

The pilot has four authored paraphrases for each of 280 scenarios. Two fixture variants validate 560 command executions. This verifies supported command labels, not every possible shell environment, and does not establish strong paraphrase or composition generalization. Exact normalized overlap checks do not detect all semantic similarity. Our existing 112-case evaluation suite is a development benchmark; reserve a separate blinded test set before making final quality claims.

Next data work should follow observed failures, introduce genuinely different request structures, and add controlled composition holdouts.
