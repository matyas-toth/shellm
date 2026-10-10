"""Exercise public-upload boundaries and incremental commits without contacting HF."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from huggingface_hub import CommitOperationAdd
from huggingface_hub.hf_api import RepoFile

from tools import sync_hf


class ManualSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.epoch = self.root / "checkpoints" / "run-a" / "epoch-1"
        self.epoch.mkdir(parents=True)
        self.write("adapter_model.safetensors", b"saved weights")
        self.write("adapter_config.json", b'{"peft_type":"LORA"}')
        self.write("training-metadata.json", json.dumps({
            "run_id": "run-a", "epoch": 1,
            "adapter_sha256": hashlib.sha256(b"saved weights").hexdigest()}).encode())

    def write(self, name, content):
        (self.epoch / name).write_bytes(content)

    def remote_file(self, file, lfs=False):
        options = {"path": file.destination, "size": file.size, "oid": file.git_blob}
        if lfs:
            options["lfs"] = {"size": file.size, "oid": file.sha256, "pointerSize": 130}
        return RepoFile(**options)

    def api(self, entries):
        api = Mock()
        api.repo_info.return_value = SimpleNamespace(sha="a" * 40)
        api.list_repo_tree.return_value = entries
        api.create_commit.return_value = SimpleNamespace(commit_url="https://huggingface.co/org/model/commit/test")
        return api

    def test_preview_never_constructs_an_api_client(self):
        files = sync_hf.collect_files(self.root)
        with patch.object(sync_hf, "collect_files", return_value=files), \
                patch.object(sync_hf, "HfApi") as constructor, redirect_stdout(io.StringIO()):
            sync_hf.main(["--repo", "org/model"])
        constructor.assert_not_called()

    def test_selection_skips_partial_epochs_and_excludes_unrelated_files(self):
        self.write("token.txt", b"private value")
        unfinished = self.epoch.parent / "epoch-2"
        unfinished.mkdir()
        (unfinished / "adapter_model.safetensors").write_bytes(b"partial")
        report = self.root / "reports" / "run-a"
        report.mkdir(parents=True)
        (report / "evaluation.json").write_text("{}")
        (report / ".env").write_text("private")
        other = self.root / "reports" / "run-b"
        other.mkdir()
        (other / "evaluation.json").write_text("{}")
        with redirect_stdout(io.StringIO()):
            files = sync_hf.collect_files(self.root, ["run-a"])
        destinations = {f.destination for f in files}
        self.assertIn("reports/run-a/evaluation.json", destinations)
        self.assertEqual(len(destinations), 4)
        self.assertTrue(all("epoch-2" not in p and "run-b" not in p and "token.txt" not in p for p in destinations))

    def test_checkpoint_fingerprint_and_run_selection_are_checked(self):
        self.write("adapter_model.safetensors", b"truncated")
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            sync_hf.collect_files(self.root)
        with self.assertRaisesRegex(ValueError, "Invalid run ID"):
            sync_hf.collect_files(self.root, ["../run-a"])

    def test_unchanged_git_and_lfs_files_create_no_commit(self):
        files = sync_hf.collect_files(self.root)
        api = self.api([self.remote_file(f, lfs=f.source.suffix == ".safetensors") for f in files])
        with patch.object(sync_hf, "ROOT", self.root), redirect_stdout(io.StringIO()):
            self.assertIsNone(sync_hf.upload(files, "org/model", api=api))
        api.create_commit.assert_not_called()

    def test_only_new_or_changed_reports_are_committed_without_deletions(self):
        files = sync_hf.collect_files(self.root)
        api = self.api([self.remote_file(f) for f in files])
        report = self.root / "reports" / "run-a" / "evaluation.json"
        report.parent.mkdir(parents=True)
        report.write_text('{"functional_ok":1}')
        files.append(sync_hf.describe_file(report, "reports/run-a/evaluation.json", self.root))
        with patch.object(sync_hf, "ROOT", self.root), redirect_stdout(io.StringIO()):
            sync_hf.upload(files, "org/model", api=api)
        options = api.create_commit.call_args.kwargs
        self.assertEqual(options["parent_commit"], "a" * 40)
        self.assertEqual(options["repo_id"], "org/model")
        self.assertEqual(len(options["operations"]), 1)
        self.assertIsInstance(options["operations"][0], CommitOperationAdd)
        self.assertEqual(options["operations"][0].path_in_repo, "reports/run-a/evaluation.json")

    def test_existing_adapter_collision_is_rejected_before_any_commit(self):
        files = sync_hf.collect_files(self.root)
        weights = next(f for f in files if f.source.suffix == ".safetensors")
        existing = RepoFile(path=weights.destination, size=weights.size, oid="different")
        api = self.api([existing])
        with self.assertRaisesRegex(ValueError, "Existing adapter differs"):
            sync_hf.upload(files, "org/model", api=api)
        api.create_commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
