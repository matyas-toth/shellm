# Manual Hugging Face progress sync

Date: 2026-10-10 (Europe/Budapest).

## Purpose and completed work

The user reported creating an organization model repository and requested a reusable script to sync progress when explicitly triggered. They had received commands for a one-time full-checkpoint upload; successful execution of that upload has not been confirmed in this chat.

Added `tools/sync_hf.py`. It is a standalone manual command with a local preview by default and an explicit `--upload` mode. No training hook, scheduler, or automatic upload was added. No live Hugging Face upload was performed during implementation.

`huggingface-hub==0.36.2` was already present in the user's modified project dependencies. This step preserves those dependency changes and uses the existing WSL environment and SDK. No model was loaded or trained.

## Repository layout

The script preserves the remote `adapters` layout used in the earlier manual upload:

```text
adapters/
  <run-id>/
    epoch-1/
      adapter_config.json
      adapter_model.safetensors
      tokenizer files, README.md, training-metadata.json
    epoch-2/
    epoch-3/
reports/
  <run-id>/
    training metadata and logs, evaluation JSON, predictions JSONL, charts
  history.csv
```

Checkpoint files use an explicit filename allowlist: adapter weights/config, saved checkpoint metadata, model card, and known tokenizer files. A checkpoint is included only when the weight, configuration and checkpoint-metadata files exist and its run/epoch identity and weight SHA-256 match that metadata. Incomplete epochs are skipped. Empty directories contain no uploadable files.

By default the script also selects `.json`, `.jsonl`, `.csv`, `.png`, `.svg` and `.md` files under `reports/`. Hidden paths, console `.log` files, and source snapshot `.py` files are excluded. JSONL training logs are included. This is a selected progress archive, not a complete backup of all report-directory contents. GitHub's ignored `checkpoints/` and safetensors rules do not prevent this explicit Hub upload.

With `--run-id`, checkpoint/report selection is restricted to that run. The global `reports/history.csv` is also included and can reference other locally recorded runs. Without `--run-id`, all local saved epochs and allowed report files are considered, including standalone evaluation runs and failed-attempt report metadata.

The script keeps the existing repository root model card and default model files as they are. Choosing an adapter for easy root-level loading is a separate future publication decision.

## Commands in WSL

From Windows PowerShell, enter `wsl -d Ubuntu`. Then:

```bash
cd /mnt/c/Users/reign/Documents/ChatGPT/SheLLM-0.6B-Project
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
export SHELLM_HF_REPO="YOUR_ORG/ShellLM-0.6B"
```

Replace `YOUR_ORG` with the organization's actual namespace. `--repo ORG/model` can be passed directly instead of setting `SHELLM_HF_REPO`. An explicit organization/user namespace is required.

### Preview a selected experiment

```bash
uv run python tools/sync_hf.py \
  --repo "$SHELLM_HF_REPO" \
  --run-id 2026-10-10-pilot-v2-fresh-lora-expandable
```

The preview lists candidate remote paths, file count and total local size. It does not contact the Hub, inspect remote files or require authentication. Its candidate count includes files that may already be uploaded. Hashing large local checkpoint files can take a few seconds.

### Sync that experiment when desired

```bash
uv run python tools/sync_hf.py \
  --repo "$SHELLM_HF_REPO" \
  --run-id 2026-10-10-pilot-v2-fresh-lora-expandable \
  --upload
```

For all local progress, omit `--run-id`:

```bash
uv run python tools/sync_hf.py --repo "$SHELLM_HF_REPO" --upload
```

Use `--weights-only` to include the checkpoint folders without report/chart files. Repeat `--run-id` to select multiple experiments. `--commit-message "Description"` supplies a custom commit message. Default commit messages use Europe/Budapest date and time.

Uploads use the authentication saved by `uv run hf auth login`, or the SDK's normal `HF_TOKEN` environment support. Tokens are not script arguments or saved in project files. The target model repository must already exist, use `main`, and grant the authenticated account write permission; the script does not create repositories or change visibility.

## Incremental behavior and decisions

In `--upload` mode, the script reads the current `main` head and its complete file tree. It compares local Git blob SHA-1 against ordinary remote files and local SHA-256 against remote LFS/Xet-backed weight metadata. Matching files are skipped. The SDK handles uploading the added/updated contents.

New and changed files are submitted in one Hugging Face commit. If everything matches, no commit is created. This avoids creating commits simply because the sync command was run again. There are no deletion operations: removing a local file does not remove its archived remote copy.

Existing adapter weights or adapter configurations that differ at the same run/epoch path cause a failure before committing. Use a new run/epoch identity for a changed model. Other selected artifacts, such as reports, may be updated as an experiment progresses. Weight fingerprints are checked independently of the remote comparison.

The commit is tied to the head used for comparison with `parent_commit`, so a concurrent remote change fails rather than applying an outdated comparison; rerun the sync. Changed local sources are rechecked before committing. Trigger sync after training/evaluation has finished writing the files; this command is not a live backup of active processes. A failed upload exits with an error; rerunning after resolving it compares the remote state again.

The command does not load an adapter, execute generated shell commands, evaluate models, refresh report history or generate charts. Those steps should be completed first when syncing their results. The archive records whichever validated model and observed reports are present locally.

SDK reference: [HfApi create_commit](https://huggingface.co/docs/huggingface_hub/v0.36.0/en/package_reference/hf_api#huggingface_hub.HfApi.create_commit).

## Verification and observed results

```bash
uv run python -m unittest discover -s tests -p test_hf_sync.py -v
```

Six tests in `tests/test_hf_sync.py` passed using temporary files and a mocked API. They check that preview never constructs a network client, incomplete/irrelevant files are excluded, corrupt checkpoint metadata and traversal IDs are rejected, ordinary and LFS matches create no commit, a new report produces an addition without deletions with the expected parent commit, and conflicting archived weights fail before committing.

A real local preview of the pilot-v2 run passed: 65 candidate files, 105.7 MiB, including three saved epochs and selected reports/history. The all-progress preview also passed: 215 candidate files, 317.0 MiB. These previews verify local selection and adapter hashes, not remote permissions or a successful upload. Live remote sync remains untested because publishing was not requested for this milestone. `git diff --check` passed.

## Next step

Run the preview with the actual repository ID. When the user decides to sync progress, invoke the same command with `--upload` and preserve its resulting commit URL. Further automatic training integration is outside this milestone.
