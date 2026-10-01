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

## Pilot v1

| Property | Value |
| --- | ---: |
| Examples | 1,120 |
| Training / validation | 1,008 / 112 |
| Families | 14 |
| Examples per family | 80 |
| Intent groups | 280 |
| Paraphrases per group | 4 |
| Unique command strings | 261 |
| Label executions checked | 560 |
| Normalized request overlap with evaluation | 0 |

Each group stays entirely in one split. Most families hold out `tundra` and `zephyr` argument scenarios; `pwd` holds out phrasing groups. Equivalent `pwd` labels recur because they express the same operation. This is a small, balanced pilot with authored templates and slot variations. Its size does not imply 1,008 independent linguistic patterns or comprehensive Linux coverage.

## Reproduce and validate

Run inside WSL from the repository root:

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv run python -m shellm_data build --release pilot-v1 --check
uv run python -m shellm_data validate --release pilot-v1
```

The first command proves the committed examples match the source catalogs. The second executes each group's command in two generated disposable Docker fixtures and checks output, working directory, and filesystem against an independent Python intent oracle. Shared paraphrases share a command validation; each English request still requires human semantic review. Successful execution alone cannot prove a paraphrase describes the right command.

`manifest.json` records content and shard hashes. `validation.json` ties successful checks to the dataset, validator, and Docker image. The trainer rejects changed shards and stale intent validation. Existing releases are preserved: the compiler refuses to overwrite them. The unrelated `data/distro_cmds/` inventory is not training data for this experiment.
