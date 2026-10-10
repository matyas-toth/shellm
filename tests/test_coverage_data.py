"""The expanded release preserves its parent and exercises meaningful contrasts."""

from collections import defaultdict
import unittest

from shellbench.sandbox import docker_cli, image_id, run_container
from shellm_data.core import build, load_release, source_groups
from shellm_data.intents import check_intent, make_fixture, render


class CoverageReleaseTests(unittest.TestCase):
    def test_parent_scenarios_are_preserved_exactly(self):
        previous = {g["id"]: {k: v for k, v in g.items() if k != "source"} for g in source_groups("pilot-v1")}
        current = {g["id"]: {k: v for k, v in g.items() if k != "source"} for g in source_groups("pilot-v2")}
        self.assertEqual({gid: current[gid] for gid in previous}, previous)

    def test_new_labels_do_not_cross_splits(self):
        rows, manifest = load_release("pilot-v2")
        self.assertEqual(build("pilot-v2", check=True), manifest)
        labels = defaultdict(set)
        for row in rows:
            if row["group_id"].startswith("coverage-v2-"):
                labels[row["command"]].add(row["split"])
        self.assertTrue(all(len(splits) == 1 for splits in labels.values()))

    def test_redirection_requires_a_separate_destination(self):
        for intent in ({"op": "cat", "sources": ["a"], "append": True},
                       {"op": "cat", "sources": ["a"], "output": "./a"}):
            with self.assertRaises(ValueError):
                render(intent)


class CoverageContrastTests(unittest.TestCase):
    def test_oracle_accepts_equivalents_and_rejects_missing_constraints(self):
        cases = []

        def contrast(intent, wrong, equivalent=None):
            cases.append((intent, render(intent), True))
            cases.append((intent, wrong, False))
            if equivalent:
                cases.append((intent, equivalent, True))

        contrast({"op": "touch", "targets": ["invoice;paid.txt"]}, "touch invoice paid.txt")
        contrast({"op": "touch", "targets": ["invoice $cost.txt"]}, 'touch "invoice $cost.txt"')
        contrast({"op": "ls", "directory": "catalog", "all": True}, "ls catalog", "ls -a catalog")
        contrast({"op": "ls", "directory": "catalog", "one": True}, "find catalog -type f")
        contrast({"op": "head", "source": "ledger.txt", "count": 7, "bytes": True}, "head -n 7 ledger.txt")
        contrast({"op": "tail", "source": "ledger.txt", "count": 1}, "head -n 1 ledger.txt")
        for flag, option in (("ignore_case", "i"), ("invert", "v"), ("line_numbers", "n"), ("count", "c")):
            contrast({"op": "grep", "source": "ledger.txt", "pattern": "NOTICE.x", flag: True}, "grep -F -- NOTICE.x ledger.txt")
        contrast({"op": "grep", "source": ".", "pattern": "NOTICE.x", "recursive": True},
                 "find . -type f -name 'NOTICE.x'", "grep -rFl -- NOTICE.x .")
        contrast({"op": "grep", "source": "ledger.txt", "pattern": "NOTICE.x"}, "grep -- NOTICE.x ledger.txt")
        contrast({"op": "find", "directory": "tree", "type": "f", "size_gt": 64},
                 "find tree -type f -size +63c", "find tree -size +64c -type f")
        contrast({"op": "find", "directory": "tree", "type": "f", "pattern": "*.csv"}, "find tree -type f")
        contrast({"op": "find", "directory": "tree", "type": "f", "maxdepth": 1}, "find tree -type f")
        contrast({"op": "find", "directory": "tree", "type": "f", "maxdepth": 2}, "find tree -type f")
        contrast({"op": "find", "directory": "tree", "type": "d", "empty": True}, "find tree -type d")
        contrast({"op": "find", "directory": "tree", "type": "f", "pattern": "*.csv", "size_gt": 64, "maxdepth": 2},
                 "find tree -maxdepth 2 -type f -name '*.csv'")
        contrast({"op": "cat", "sources": ["a.txt", "b.txt"], "output": "joined.txt"},
                 "cat b.txt a.txt > joined.txt", "cat -- a.txt b.txt > joined.txt")
        contrast({"op": "cat", "sources": ["a.txt"], "output": "joined.txt", "append": True},
                 "cat a.txt > joined.txt", "cat < a.txt >> joined.txt")
        contrast({"op": "cat", "sources": ["a.txt"], "output": "joined.txt"}, "cat a.txt >> joined.txt")
        contrast({"op": "cat", "sources": ["a.txt"]}, "tee joined.txt < a.txt")
        items = [{"id": str(i), "command": command, "fixtures": [make_fixture(intent, seed) for seed in (0, 1)]}
                 for i, (intent, command, _) in enumerate(cases)]
        outcomes = run_container(docker_cli(), image_id(docker_cli()), items, [make_fixture({"op": "pwd"}, 0)] * 2)
        for i, (intent, command, accepted) in enumerate(cases):
            for spec, outcome in zip(items[i]["fixtures"], outcomes[str(i)], strict=True):
                with self.subTest(intent=intent, command=command, seed=spec):
                    if accepted:
                        check_intent(intent, spec, outcome)
                    else:
                        with self.assertRaises(ValueError):
                            check_intent(intent, spec, outcome)


if __name__ == "__main__":
    unittest.main()
