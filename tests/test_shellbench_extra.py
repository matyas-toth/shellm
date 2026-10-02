"""Extra gates: independence, behavioral equivalence, errors, and fixture variation."""

import copy
import unittest

from shellbench.extra_audit import audit
from shellbench.extra_fixtures import fixture
from shellbench.extra_oracle import expression
from shellbench.sandbox import compare, docker_cli, image_id, load_cases, reference_results, run_container, same_stdout
from shellbench.suites import suite_path
from shellm_data.core import check_records, load_release


class ExtraIntegrityTests(unittest.TestCase):
    def test_frozen_suite_is_separate_from_all_training_splits(self):
        report = audit(load_cases(suite_path("shellbench-extra-v1")))
        self.assertEqual(report["cases"], 300)
        self.assertEqual(report["training_and_validation_request_overlap"], 0)
        self.assertEqual(report["exact_existing_command_overlap"], 0)

    def test_future_training_rejects_reserved_extra_request(self):
        rows, _ = load_release()
        rows = copy.deepcopy(rows)
        rows[0]["request"] = load_cases(suite_path("shellbench-extra-v1"))[0]["request"]
        with self.assertRaisesRegex(ValueError, "evaluation-overlapping"):
            check_records(rows)

    def test_number_mode_rejects_output_labels(self):
        self.assertTrue(same_stdout(" 12\n", "12\n", "number"))
        self.assertFalse(same_stdout("12 wrong.txt\n", "12\n", "number"))

    def test_future_training_rejects_reserved_extra_command(self):
        rows, _ = load_release()
        row = copy.deepcopy(next(row for row in rows if row["family"] == "mkdir"))
        row.update(request="Prepare a directory with this reserved concrete target", command="mkdir 'lab/work/release notes'",
                   intent={"op": "mkdir", "targets": ["lab/work/release notes"]})
        with self.assertRaisesRegex(ValueError, "Command label reserved"):
            check_records([row])

    def test_reference_expectations_vary_between_worlds(self):
        cases = load_cases(suite_path("shellbench-extra-v1"))
        changed = sum(expression(case["expectation"]["stdout"], fixture(0)) != expression(case["expectation"]["stdout"], fixture(1)) for case in cases)
        self.assertGreater(changed, 70)


class ExtraDockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli, cls.fixtures = docker_cli(), [fixture(0), fixture(1)]
        cls.image = image_id(cls.cli)
        cls.cases = {case["id"]: case for case in load_cases(suite_path("shellbench-extra-v1"))}
        cls.references = reference_results(cls.cli, cls.image, list(cls.cases.values()), cls.fixtures)

    def check(self, case_id, command, passes):
        outputs = run_container(self.cli, self.image, [{"id": case_id, "command": command}], self.fixtures)[case_id]
        comparisons = [compare(actual, expected, self.cases[case_id]["comparison"]) for actual, expected in zip(outputs, self.references[case_id], strict=True)]
        self.assertEqual(all(not reasons for reasons in comparisons), passes, (case_id, command, comparisons))

    def test_alternative_commands_across_all_twenty_categories(self):
        commands = {
            "navigation": (1, "cd /./ && pwd"),
            "listing": (2, "find lab -mindepth 1 -maxdepth 1 -printf '%f\\n'"),
            "mkdir": (1, "mkdir -- 'lab/work/release notes'"),
            "touch": (1, ": > 'lab/work/release notes.md'"),
            "copy": (1, "cat 'lab/client files/quarter one.txt' > 'lab/archive/quarter copy.txt'"),
            "move": (1, "cp 'lab/client files/quarter one.txt' 'lab/client files/quarter revised.txt' && rm 'lab/client files/quarter one.txt'"),
            "remove": (1, "unlink 'lab/client files/quarter one.txt'"),
            "read": (1, "sed -n p 'lab/client files/quarter one.txt'"),
            "slice": (1, "sed -n '1,3p' lab/prose.txt"),
            "count": (1, "awk 'END {print NR}' lab/prose.txt"),
            "grep": (1, "grep 'needle\\.a' lab/messages.txt"),
            "find": (3, "find lab/scan -size +100c -name '*.dat' -type f | sort"),
            "sort": (2, "sort --numeric-sort lab/amounts.txt"),
            "transform": (6, "awk '{gsub(/FAIL/,\"ALERT\"); print}' lab/messages.txt"),
            "fields": (7, "awk '$2==\"red\" {print $1}' lab/ledger.tsv"),
            "write": (3, "echo added >> lab/work/stay.txt"),
            "permissions": (1, "chmod u=rw,go= lab/raw/readme.txt"),
            "links": (1, "ln --symbolic prose.txt lab/prose-link"),
            "pipeline": (3, "sort -unr lab/amounts.txt | sed -n '1,3p'"),
            "conditional": (1, "test ! -e lab/gate.ok || touch lab/work/allowed.txt"),
        }
        for family, (number, command) in commands.items():
            with self.subTest(family=family):
                self.check(f"extra-v1-{family}-{number:02d}", command, True)

    def test_wrong_commands_across_all_twenty_categories(self):
        commands = {
            "navigation": (1, "pwd"), "listing": (2, "ls -1 lab"),
            "mkdir": (1, "mkdir lab/work/release notes"), "touch": (1, "touch lab/work/release-notes.md"),
            "copy": (1, "mv 'lab/client files/quarter one.txt' 'lab/archive/quarter copy.txt'"),
            "move": (1, "cp 'lab/client files/quarter one.txt' 'lab/client files/quarter revised.txt'"),
            "remove": (1, "rm 'lab/client files/quarter one.txt' lab/work/stay.txt"),
            "read": (1, "cat lab/prose.txt"), "slice": (1, "tail -n 3 lab/prose.txt"),
            "count": (1, "printf '999\\n'"), "grep": (1, "grep 'needle.a' lab/messages.txt"),
            "find": (3, "find lab/scan -type f -name '*.dat'"), "sort": (2, "sort lab/amounts.txt"),
            "transform": (6, "sed 's/WARN/ALERT/g' lab/messages.txt"), "fields": (7, "cut -f2 lab/ledger.tsv"),
            "write": (3, "echo added > lab/work/stay.txt"), "permissions": (1, "chmod 644 lab/raw/readme.txt"),
            "links": (1, "cp lab/prose.txt lab/prose-link"), "pipeline": (3, "sort -ru lab/amounts.txt | head -n 3"),
            "conditional": (1, "touch lab/work/allowed.txt"),
        }
        for family, (number, command) in commands.items():
            with self.subTest(family=family):
                self.check(f"extra-v1-{family}-{number:02d}", command, False)

    def test_file_type_pruning_and_unrelated_writes_are_detected(self):
        self.check("extra-v1-find-01", "find lab/scan -name '*.dat'", False)
        self.check("extra-v1-find-05", "find lab/logs -type f -name '*.log' -size +100c", False)
        self.check("extra-v1-read-01", "cat 'lab/client files/quarter one.txt'; rm lab/work/stay.txt", False)


if __name__ == "__main__":
    unittest.main()
