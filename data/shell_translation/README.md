# English to shell training data

These small, fully rendered datasets belong in Git. Training needs no API calls, paraphrase generation, or hidden data downloads. The authoritative editable sources are command intent catalogs; the rendered releases expose every English request and command label for review.

## Layout

```text
data/shell_translation/
  catalogs/
    pilot-v1/
      navigation/{pwd,cd}.json
      filesystem/{ls,mkdir,touch,cp,mv,rm}.json
      text/{cat,head,tail,wc,grep}.json
      search/find.json
  releases/
    pilot-v1/
      families/<topic>/<family>.jsonl
      manifest.json
      validation.json
```

Each catalog is a JSON array of scenario groups. For example:

```json
{
  "id": "pilot-v2-mkdir-backups",
  "topic": "filesystem",
  "family": "mkdir",
  "capability": "directory-creation",
  "split": "train",
  "intent": {"op": "mkdir", "targets": ["backups"]},
  "requests": ["create a directory named backups", "make a folder called backups"]
}
```

The compiler renders `mkdir backups`, assigns stable example IDs using the group ID and paraphrase position, and stores both the intent and source provenance on every JSONL record. Append requests to preserve existing IDs; use a new group ID when changing a scenario. Read [the contribution guide](../../docs/training-data-contribution-guide.md) before creating a release.

## Current release: pilot-v2

Prepared, approved and trained on 2026-10-10. [The completed fresh LoRA experiment](../../docs/pilot-v2-fresh-lora-experiment.md) scored 92.9% on ShellBench v1 and 34.3% on Extra v1. It is a complete snapshot: load `pilot-v2` alone to include the parent data and additions.

| Property | Value |
| --- | ---: |
| Examples | 22,784 |
| Training / validation | 18,392 / 4,392 |
| Added examples | 20,340 |
| Families | 74 |
| Scenario groups | 4,001 |
| Unique command strings | 3,959 |

Browse `catalogs/pilot-v2/<topic>/<family>.json` for editable intents/requests and `releases/pilot-v2/families/<topic>/<family>.jsonl` for full labels. [The review pack](authoring/pilot-v2/review.md) shows samples from every added capability. [Coverage](authoring/pilot-v2/coverage.json), [quality checks](authoring/pilot-v2/quality.json), and [functional validation](releases/pilot-v2/validation.json) preserve machine-readable evidence. Read [the milestone notebook](../../docs/pilot-v2-coverage-data-expansion.md) for splits, provenance and limitations.

All 611 parent scenarios are preserved exactly. New validation uses disjoint argument roots and separate sentence banks. This is a complete, template-based authored release, not a claim of 22,784 independent language patterns. The new split does not independently hold out compositions.

After approval, future contributors should copy the current catalogs to a new release such as `pilot-v3`, preserving both existing rendered releases. `tools/build_coverage_catalog.py` preserves the pilot-v2 authoring matrix; `tools/audit_coverage_release.py` exports the review and quality checks without loading model weights or training.

## Pilot v1 (preserved parent)

| Property | Value |
| --- | ---: |
| Examples | 2,444 |
| Training / validation | 2,072 / 372 |
| Families | 74 |
| Intent groups | 611 |
| Paraphrases per group | 4 |
| Unique command strings | 577 |
| Label executions checked | 1,222 |
| Normalized request overlap with evaluation | 0 |

The original pilot contained 1,008 training and 112 validation examples across 14 families; chmod and utility additions expanded it to the preserved counts above. Each group stays entirely in one split. Original families mostly hold out `tundra` and `zephyr` argument scenarios; `pwd` holds out phrasing groups. Equivalent `pwd` labels recur because they express the same operation. See the notebook for the individual expansion experiments.

## Reproduce and validate

Run inside WSL from the repository root:

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv run python -m shellm_data build --release pilot-v2 --check
uv run python -m shellm_data validate --release pilot-v2
uv run python tools/audit_coverage_release.py
```

The first command proves the committed examples match the source catalogs. The second executes each group's command in two generated disposable Docker fixtures and checks output, working directory, and filesystem against an independent Python intent oracle. Shared paraphrases share a command validation; each English request still requires human semantic review. Successful execution alone cannot prove a paraphrase describes the right command.

`manifest.json` records content and shard hashes. `validation.json` ties successful checks to the dataset, validator, and Docker image. The trainer rejects changed shards and stale intent validation. Existing releases are preserved: the compiler refuses to overwrite them. The unrelated `data/distro_cmds/` inventory is not training data for this experiment.
