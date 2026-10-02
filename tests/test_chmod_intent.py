"""Chmod intent rendering, validation, and Docker-backed oracle behavior."""

import unittest

from shellbench.sandbox import docker_cli, image_id, run_container
from shellm_data.intents import check_intent, make_fixture, render, validate_intent

PLAIN = {"op": "chmod", "targets": ["demo script.sh"], "mode": "700"}
RECURSIVE = {"op": "chmod", "targets": ["shared"], "mode": "755", "recursive": True}


class ChmodRenderTests(unittest.TestCase):
    def test_render(self):
        self.assertEqual(render(PLAIN), "chmod 700 'demo script.sh'")
        self.assertEqual(render(RECURSIVE), "chmod -R 755 shared")
        self.assertEqual(render({"op": "chmod", "targets": ["-odd.sh"], "mode": "644"}), "chmod 644 -- -odd.sh")

    def test_invalid_intents_are_rejected(self):
        for bad in ({"op": "chmod", "targets": ["a"]},
                    {"op": "chmod", "targets": ["a"], "mode": "9"},
                    {"op": "chmod", "targets": ["a"], "mode": "u+x"},
                    {"op": "chmod", "targets": ["a"], "mode": "700", "typo": True}):
            with self.assertRaises(ValueError, msg=bad):
                validate_intent(bad)


def change(who, op, perms):
    return {"who": who, "op": op, "perms": perms}


SYMBOLIC = {"op": "chmod", "targets": ["run.sh"], "changes": [change("u", "+", "x")]}
TRIPLE = {"op": "chmod", "targets": ["k.key"], "changes": [change("u", "=", "rw"), change("g", "=", "r"), change("o", "=", "")]}
RECURSIVE_SYMBOLIC = {"op": "chmod", "targets": ["shared"], "changes": [change("g", "+", "w")], "recursive": True}
DIRECTORY = {"op": "chmod", "targets": ["folder"], "mode": "750", "directory_target": True}


class ChmodSymbolicRenderTests(unittest.TestCase):
    def test_render(self):
        self.assertEqual(render(SYMBOLIC), "chmod u+x run.sh")
        self.assertEqual(render(TRIPLE), "chmod u=rw,g=r,o= k.key")
        self.assertEqual(render(RECURSIVE_SYMBOLIC), "chmod -R g+w shared")
        self.assertEqual(render(DIRECTORY), "chmod 750 folder")
        self.assertEqual(render({"op": "chmod", "targets": ["a"], "changes": [change("go", "-", "w")]}), "chmod go-w a")

    def test_invalid_symbolic_intents_are_rejected(self):
        base = {"op": "chmod", "targets": ["a"]}
        for bad in ({**base},
                    {**base, "mode": "700", "changes": [change("u", "+", "x")]},
                    {**base, "changes": []},
                    {**base, "changes": [change("x", "+", "r")]},
                    {**base, "changes": [change("u", "+", "")]},
                    {**base, "changes": [change("u", "?", "r")]},
                    {**base, "changes": [change("u", "+", "xw")]},
                    {**base, "changes": [{"who": "u", "op": "+"}]},
                    {**base, "changes": [change("u", "-", "x")], "recursive": True},
                    {**base, "changes": [change("a", "=", "w")], "recursive": True},
                    {**base, "mode": "700", "recursive": True, "directory_target": True}):
            with self.assertRaises(ValueError, msg=bad):
                validate_intent(bad)


class ChmodOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = docker_cli()
        cls.image = image_id(cls.cli)

    def accepts(self, intent, command):
        fixtures = [make_fixture(intent, seed) for seed in (0, 1)]
        outcomes = run_container(self.cli, self.image, [{"id": "t", "command": command, "fixtures": fixtures}],
                                 [make_fixture({"op": "pwd"}, 0)] * 2)["t"]
        try:
            for spec, outcome in zip(fixtures, outcomes, strict=True):
                check_intent(intent, spec, outcome)
        except ValueError:
            return False
        return True

    def test_rendered_and_equivalent_commands_pass(self):
        self.assertTrue(self.accepts(PLAIN, render(PLAIN)))
        self.assertTrue(self.accepts(PLAIN, "chmod u=rwx,go= 'demo script.sh'"))
        self.assertTrue(self.accepts(RECURSIVE, render(RECURSIVE)))
        self.assertTrue(self.accepts(RECURSIVE, "find shared -exec chmod 755 {} +"))

    def test_wrong_commands_fail(self):
        self.assertFalse(self.accepts(PLAIN, "true"))
        self.assertFalse(self.accepts(PLAIN, "chmod 600 'demo script.sh'"))
        self.assertFalse(self.accepts(PLAIN, "chmod 700 'demo script.sh' keep/untouched.txt"))
        self.assertFalse(self.accepts(RECURSIVE, "chmod 755 shared"))
        self.assertFalse(self.accepts(RECURSIVE, "chmod -R 700 shared"))

    def test_unquoted_name_with_space_fails(self):
        self.assertFalse(self.accepts(PLAIN, "chmod 700 demo script.sh"))

    def test_leading_dash_target_requires_double_dash(self):
        dash = {"op": "chmod", "targets": ["-odd.sh"], "mode": "644"}
        self.assertTrue(self.accepts(dash, render(dash)))
        self.assertTrue(self.accepts(dash, "chmod 644 ./-odd.sh"))
        self.assertFalse(self.accepts(dash, "chmod 644 -odd.sh"))

    def test_changing_only_one_of_two_targets_fails(self):
        pair = {"op": "chmod", "targets": ["a.sh", "b.sh"], "mode": "755"}
        self.assertTrue(self.accepts(pair, render(pair)))
        self.assertFalse(self.accepts(pair, "chmod 755 a.sh"))

    def test_symbolic_commands(self):
        self.assertTrue(self.accepts(SYMBOLIC, render(SYMBOLIC)))
        self.assertTrue(self.accepts(SYMBOLIC, "chmod 744 run.sh"))
        self.assertFalse(self.accepts(SYMBOLIC, "chmod 755 run.sh"))
        self.assertFalse(self.accepts(SYMBOLIC, "chmod a+x run.sh"))
        self.assertTrue(self.accepts(TRIPLE, render(TRIPLE)))
        self.assertTrue(self.accepts(TRIPLE, "chmod 640 k.key"))
        self.assertFalse(self.accepts(TRIPLE, "chmod 600 k.key"))

    def test_recursive_symbolic_uses_each_entry_start_mode(self):
        self.assertTrue(self.accepts(RECURSIVE_SYMBOLIC, render(RECURSIVE_SYMBOLIC)))
        self.assertTrue(self.accepts(RECURSIVE_SYMBOLIC, "find shared -type d -exec chmod 775 {} + ; find shared -type f -exec chmod 664 {} +"))
        self.assertFalse(self.accepts(RECURSIVE_SYMBOLIC, "chmod -R 775 shared"))
        self.assertFalse(self.accepts(RECURSIVE_SYMBOLIC, "chmod g+w shared"))

    def test_directory_target_changes_only_the_directory(self):
        self.assertTrue(self.accepts(DIRECTORY, render(DIRECTORY)))
        self.assertFalse(self.accepts(DIRECTORY, "chmod -R 750 folder"))
        self.assertFalse(self.accepts(DIRECTORY, "chmod 700 folder"))


if __name__ == "__main__":
    unittest.main()
