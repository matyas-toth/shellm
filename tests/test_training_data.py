"""Training gates: leakage, label integrity, completion masking, and padding."""

import copy
import unittest

from transformers import AutoTokenizer

from shellm_data.core import build, check_records, load_release
from shellm_data.intents import render
from shellm_training.data import collate, tokenize_record


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.manifest = load_release("pilot-v1")

    def test_release_reproduces_catalogs(self):
        self.assertEqual(build("pilot-v1", check=True), self.manifest)

    def test_group_split_leakage_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[1]["split"] = "validation"
        with self.assertRaisesRegex(ValueError, "Group spans"):
            check_records(rows)

    def test_existing_eval_request_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        from shellbench.sandbox import load_cases
        rows[0]["request"] = load_cases()[0]["request"]
        with self.assertRaisesRegex(ValueError, "evaluation-overlapping"):
            check_records(rows)

    def test_changed_label_is_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["command"] = "true"
        with self.assertRaisesRegex(ValueError, "Label does not match"):
            check_records(rows)

    def test_arguments_are_shell_quoted(self):
        self.assertEqual(render({"op": "mkdir", "targets": ["my stuff", "-x"]}), "mkdir -- 'my stuff' -x")
        self.assertEqual(render({"op": "cat", "sources": ["$(id).txt"]}), "cat '$(id).txt'")

    def test_unknown_fields_and_invalid_counts_are_rejected(self):
        for intent in ({"op": "pwd", "typo": True}, {"op": "head", "source": "x", "count": "1; pwd"},
                       {"op": "mkdir", "targets": ["x"], "mode": "755; pwd"}):
            with self.subTest(intent=intent), self.assertRaises(ValueError):
                render(intent)


class TokenizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base", revision="da87bfb608c14b7cf20ba1ce41287e8de496c0cd")

    def test_all_examples_keep_prompt_boundary_and_eos(self):
        rows, _ = load_release("pilot-v1")
        for row in rows:
            tokens = tokenize_record(self.tokenizer, row)
            first = next(i for i, value in enumerate(tokens["labels"]) if value != -100)
            self.assertEqual(self.tokenizer.decode(tokens["input_ids"][:first]), f"Request: {row['request']}\nCommand:")
            self.assertEqual(self.tokenizer.decode(tokens["labels"][first:-1]), " " + row["command"])
            self.assertEqual(tokens["labels"][-1], self.tokenizer.eos_token_id)

    def test_padding_is_masked_and_long_examples_are_rejected(self):
        a = tokenize_record(self.tokenizer, {"id": "a", "request": "where am I", "command": "pwd"})
        b = tokenize_record(self.tokenizer, {"id": "b", "request": "make a folder named my new project files", "command": "mkdir 'my new project files'"})
        batch = collate([a, b], self.tokenizer.eos_token_id, device="cpu")
        self.assertTrue(batch["labels"][0, len(a["input_ids"]):].eq(-100).all())
        self.assertTrue(batch["attention_mask"][0, len(a["input_ids"]):].eq(0).all())
        with self.assertRaisesRegex(ValueError, "no silent truncation"):
            tokenize_record(self.tokenizer, {"id": "a", "request": "where am I", "command": "pwd"}, max_length=2)


if __name__ == "__main__":
    unittest.main()
