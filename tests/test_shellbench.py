"""Integration gates for evaluator equivalence, error detection, and boundaries."""

import unittest

from shellbench.fixtures import fixture
from shellbench.sandbox import compare, docker_cli, extract_command, image_id, load_cases, reference_results, run_container, same_stdout


class ComparisonTests(unittest.TestCase):
    def test_long_listing_ignores_time_but_checks_metadata(self):
        a = "total 4\n-rw-r--r-- 1 shellm shellm 12 Oct  1 10:00 some file.txt\n"
        b = "total 4\n-rw-r--r-- 1 shellm shellm 12 Oct  1 11:00 some file.txt\n"
        self.assertTrue(same_stdout(a, b, "listing"))
        self.assertFalse(same_stdout(a.replace("12 Oct", "13 Oct"), b, "listing"))
        self.assertFalse(same_stdout(a.replace("-rw-r--r--", "-rwxr-xr-x"), b, "listing"))
        self.assertFalse(same_stdout("some file.txt\n", b, "listing"))

    def test_format_does_not_hide_explanations_or_markdown(self):
        self.assertEqual(extract_command(" pwd\n"), ("pwd", True))
        self.assertEqual(extract_command("pwd\nThis prints a path"), ("pwd", False))
        self.assertEqual(extract_command("`pwd`"), ("`pwd`", False))
        self.assertEqual(extract_command("```bash\npwd\n```"), ("```bash", False))
        self.assertEqual(extract_command("\npwd"), ("", False))

    def test_counts_accept_pipe_output(self):
        self.assertTrue(same_stdout("3\n", " 3 report.txt\n", "count"))
        self.assertFalse(same_stdout("4\n", "3 report.txt\n", "count"))
        self.assertFalse(same_stdout("3\nextra\n", "3 report.txt\n", "count"))

    def test_unordered_lines_preserve_multiplicity(self):
        self.assertTrue(same_stdout("b\na\n", "a\nb\n", "lines"))
        self.assertFalse(same_stdout("a\na\nb\n", "a\nb\n", "lines"))


class DockerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = docker_cli()
        cls.image = image_id(cls.cli)
        cls.fixtures = [fixture(0), fixture(1)]
        cls.cases = {case["id"]: case for case in load_cases()}
        cls.references = reference_results(cls.cli, cls.image, list(cls.cases.values()), cls.fixtures)

    def check(self, case_id, command, passes):
        actual = run_container(self.cli, self.image, [{"id": case_id, "command": command}], self.fixtures)[case_id]
        reasons = [compare(a, b, self.cases[case_id]["comparison"]) for a, b in zip(actual, self.references[case_id], strict=True)]
        self.assertEqual(all(not row for row in reasons), passes, (case_id, command, reasons))

    def test_equivalent_commands_for_every_family(self):
        candidates = {
            "pwd-01": "printf '%s\\n' \"$PWD\"", "cd-01": "cd /./", "ls-04": "ls -al",
            "mkdir-01": "mkdir -- projects", "touch-01": ": > new.txt",
            "cp-01": "cat notes.txt > copy.txt", "mv-01": "cp notes.txt renamed.txt && rm notes.txt",
            "rm-01": "unlink old.log", "cat-01": "sed -n p notes.txt", "head-01": "sed -n '1,5p' README.md",
            "tail-01": "tail -5 README.md", "wc-01": "cat report.txt | wc -l",
            "grep-01": "grep TODO notes.txt", "find-01": "find . -name '*.log' -type f | sort -r",
        }
        for case_id, command in candidates.items():
            with self.subTest(case_id=case_id):
                self.check(case_id, command, True)

    def test_wrong_commands_for_every_family(self):
        candidates = {
            "pwd-01": "echo /", "cd-01": "cd", "ls-04": "ls", "mkdir-01": "true",
            "touch-01": "touch wrong.txt", "cp-01": "mv notes.txt copy.txt", "mv-01": "cp notes.txt renamed.txt",
            "rm-01": "rm notes.txt", "cat-01": "cat report.txt", "head-01": "cat README.md",
            "tail-01": "head -5 README.md", "wc-01": "echo 999", "grep-06": "grep 'a.b' notes.txt",
            "find-01": "find . -name '*.log'",
        }
        for case_id, command in candidates.items():
            with self.subTest(case_id=case_id):
                self.check(case_id, command, False)

    def test_correct_output_with_unrelated_deletion_fails(self):
        self.check("pwd-01", "pwd; rm notes.txt", False)

    def test_unquoted_argument_fails(self):
        self.check("mkdir-03", "mkdir project drafts", False)

    def test_invalid_syntax_fails(self):
        self.check("pwd-01", "echo '", False)

    def test_timeout_is_reported(self):
        outcome = run_container(self.cli, self.image, [{"id": "timeout", "command": "sleep 10"}], [fixture(0)])["timeout"][0]
        self.assertTrue(outcome["timed_out"])

    def test_root_is_read_only(self):
        outcome = run_container(self.cli, self.image, [{"id": "root", "command": "touch /etc/shellm-test"}], [fixture(0)])["root"][0]
        self.assertNotEqual(outcome["returncode"], 0)

    def test_fixtures_change_expected_counts(self):
        outputs = self.references["wc-01"]
        self.assertNotEqual(outputs[0]["stdout"], outputs[1]["stdout"])


if __name__ == "__main__":
    unittest.main()
