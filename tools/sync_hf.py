"""Manually preview or sync saved adapters and experiment progress to an existing HF model repo."""

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from huggingface_hub import CommitOperationAdd, HfApi
from huggingface_hub.hf_api import RepoFile
from huggingface_hub.utils import validate_repo_id

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_FILES = {
    "adapter_config.json", "adapter_model.safetensors", "training-metadata.json", "README.md",
    "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json",
    "vocab.json", "merges.txt", "chat_template.jinja",
}
REPORT_SUFFIXES = {".json", ".jsonl", ".csv", ".png", ".svg", ".md"}


@dataclass(frozen=True)
class LocalFile:
    source: Path
    destination: str
    size: int
    sha256: str
    git_blob: str


def describe_file(source, destination, root):
    if not source.resolve().is_relative_to(root.resolve()) or any(
        part.is_symlink() for part in (source, *source.parents) if part.is_relative_to(root)
    ):
        raise ValueError(f"Upload source must be a regular workspace file: {source}")
    size = source.stat().st_size
    sha256 = hashlib.sha256()
    git_blob = hashlib.sha1(f"blob {size}\0".encode())
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha256.update(chunk)
            git_blob.update(chunk)
    return LocalFile(source, destination, size, sha256.hexdigest(), git_blob.hexdigest())


def collect_files(root=ROOT, run_ids=None, weights_only=False):
    """Collect only finished, fingerprinted epochs and known report formats."""
    runs = set(run_ids or [])
    for run in runs:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", run):
            raise ValueError(f"Invalid run ID: {run}")
        if not (root / "checkpoints" / run).is_dir():
            raise ValueError(f"No local checkpoint run: {run}")
    files = []
    checkpoint_root = root / "checkpoints"
    for run in sorted(checkpoint_root.iterdir()) if checkpoint_root.exists() else []:
        if not run.is_dir() or runs and run.name not in runs:
            continue
        if run.is_symlink():
            raise ValueError(f"Checkpoint run is a symlink: {run}")
        for epoch in sorted(run.iterdir()):
            if not epoch.is_dir() or not re.fullmatch(r"epoch-[1-9][0-9]*", epoch.name):
                continue
            if epoch.is_symlink():
                raise ValueError(f"Checkpoint epoch is a symlink: {epoch}")
            required = ("adapter_config.json", "adapter_model.safetensors", "training-metadata.json")
            if not all((epoch / name).is_file() for name in required):
                print(f"Skipping incomplete checkpoint: {run.name}/{epoch.name}")
                continue
            selected = [describe_file(source, f"adapters/{run.name}/{epoch.name}/{source.name}", root)
                        for source in sorted(epoch.iterdir()) if source.is_file() and source.name in CHECKPOINT_FILES]
            info = json.loads((epoch / "training-metadata.json").read_text(encoding="utf-8"))
            weights = next(f for f in selected if f.source.name == "adapter_model.safetensors")
            if (info["run_id"] != run.name or f"epoch-{info['epoch']}" != epoch.name
                    or info["adapter_sha256"] != weights.sha256):
                raise ValueError(f"Checkpoint metadata/fingerprint mismatch: {epoch}")
            files.extend(selected)
    if not weights_only:
        reports = root / "reports"
        for source in sorted(reports.rglob("*")) if reports.exists() else []:
            relative = source.relative_to(reports)
            if (not source.is_file() or source.suffix not in REPORT_SUFFIXES
                    or any(part.startswith(".") for part in relative.parts)):
                continue
            if runs and relative.as_posix() != "history.csv" and relative.parts[0] not in runs:
                continue
            files.append(describe_file(source, f"reports/{relative.as_posix()}", root))
    return files


def changed_files(files, remote):
    changed = []
    for local in files:
        existing = remote.get(local.destination)
        if existing:
            digest = existing.lfs.sha256 if existing.lfs else existing.blob_id
            if existing.size == local.size and digest == (local.sha256 if existing.lfs else local.git_blob):
                continue
            if local.source.name in {"adapter_model.safetensors", "adapter_config.json"}:
                raise ValueError(f"Existing adapter differs at {local.destination}; use a new run/epoch ID")
        changed.append(local)
    return changed


def upload(files, repo, message=None, api=None):
    """One commit of additions/updates; never delete files or create a repository."""
    api = api if api is not None else HfApi()
    head = api.repo_info(repo_id=repo, repo_type="model", revision="main").sha
    remote = {entry.path: entry for entry in api.list_repo_tree(
        repo_id=repo, repo_type="model", revision=head, recursive=True) if isinstance(entry, RepoFile)}
    changed = changed_files(files, remote)
    print(f"Remote comparison: {len(changed)} new/changed, {len(files) - len(changed)} unchanged files")
    if not changed:
        print("Already synced; no commit created.")
        return None
    for file in changed:
        print(f"  Upload: {file.destination}")
    # Fail if a local source changed while comparing the remote snapshot.
    for file in changed:
        current = describe_file(file.source, file.destination, ROOT)
        if current.sha256 != file.sha256:
            raise ValueError(f"Local file changed during sync; retry once writing finishes: {file.source}")
    operations = [CommitOperationAdd(path_in_repo=f.destination, path_or_fileobj=str(f.source)) for f in changed]
    stamp = datetime.now(ZoneInfo("Europe/Budapest")).strftime("%Y-%m-%d %H:%M %Z")
    result = api.create_commit(repo_id=repo, repo_type="model", revision="main", parent_commit=head,
                               operations=operations, commit_message=message or f"Sync SheLLM progress {stamp}")
    print(f"Synced: {result.commit_url}")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("SHELLM_HF_REPO"), help="ORG/model; or set SHELLM_HF_REPO")
    parser.add_argument("--run-id", action="append", help="Only this run; repeatable. Default: all runs")
    parser.add_argument("--weights-only", action="store_true", help="Sync checkpoint folders without reports/charts")
    parser.add_argument("--upload", action="store_true", help="Actually sync; default is a local preview without network calls")
    parser.add_argument("--commit-message", help="Custom HF commit message")
    args = parser.parse_args(argv)
    if not args.repo or args.repo.count("/") != 1:
        parser.error("Provide --repo ORG/model, or set SHELLM_HF_REPO")
    validate_repo_id(args.repo)
    files = collect_files(run_ids=args.run_id, weights_only=args.weights_only)
    if not files:
        raise ValueError("No finished checkpoints or report files found for the requested selection")
    print(f"Destination: {args.repo} (model repo, main)")
    print(f"Local selection: {len(files)} files, {sum(f.size for f in files) / 1024**2:.1f} MiB")
    for file in files:
        print(f"  {file.destination}")
    if not args.upload:
        print("Preview only; remote files were not inspected. Add --upload to sync new/changed files.")
        return
    upload(files, args.repo, args.commit_message)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from error
