"""Shell utility command families: render, validation, and Docker-backed oracle behavior."""

import unittest

from shellbench.sandbox import run_container
from shellm_data.intents import check_intent, make_fixture, render, validate_intent

try:
    from .utility_helpers import UtilityCase
except ImportError:
    from utility_helpers import UtilityCase


class ShellUtilCase(UtilityCase):
    def verdicts(self, intent, commands):
        """Run all commands in one container; True where the oracle accepts a command on both fixtures."""
        fixtures = [make_fixture(intent, seed) for seed in (0, 1)]
        items = [{"id": str(i), "command": c, "fixtures": fixtures} for i, c in enumerate(commands)]
        results = run_container(self.cli, self.image, items, [make_fixture({"op": "pwd"}, 0)] * 2)
        verdicts = []
        for i in range(len(commands)):
            try:
                for spec, outcome in zip(fixtures, results[str(i)], strict=True):
                    check_intent(intent, spec, outcome)
                verdicts.append(True)
            except ValueError:
                verdicts.append(False)
        return verdicts

    def check(self, intent, command, good=(), bad=()):
        """The rendered command and every `good` command pass the oracle; every `bad` command is rejected."""
        self.assertEqual(render(intent), command)
        commands = [command, *good, *bad]
        expected = [True] * (1 + len(good)) + [False] * len(bad)
        for text, verdict, wanted in zip(commands, self.verdicts(intent, commands), expected):
            self.assertEqual(verdict, wanted, text)

    def invalid(self, *intents):
        for intent in intents:
            with self.assertRaises(ValueError, msg=str(intent)):
                validate_intent(intent)


class EchoTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "echo", "text": "hi"}), "echo hi")
        self.assertEqual(render({"op": "echo", "text": "Hello, World!"}), "echo 'Hello, World!'")
        self.assertEqual(render({"op": "echo", "text": "it's $5"}), "echo 'it'\"'\"'s $5'")
        self.invalid({"op": "echo"}, {"op": "echo", "text": "-n"}, {"op": "echo", "text": "a\\nb"},
                     {"op": "echo", "text": "x", "interpret_escapes": True}, {"op": "echo", "text": "x", "bogus": 1})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "echo", "text": "deploy complete", "no_newline": True}, "echo -n 'deploy complete'",
                   good=["printf %s 'deploy complete'"], bad=["echo 'deploy complete'", "echo -n deploy"])
        self.check({"op": "echo", "text": "it's ready now"}, "echo \"it's ready now\"",
                   good=["printf '%s\\n' \"it's ready now\""], bad=["echo its ready now", "echo -n \"it's ready now\""])
        self.check({"op": "echo", "text": 'say "hello" to everyone'}, "echo 'say \"hello\" to everyone'",
                   good=['echo "say \\"hello\\" to everyone"'], bad=["echo say hello to everyone"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "echo")


class PrintfTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "printf", "format": "%s\\n", "arguments": ["alpha", "beta"]}), "printf '%s\\n' alpha beta")
        self.assertEqual(render({"op": "printf", "format": "-%s\\n", "arguments": ["x"]}), "printf -- '-%s\\n' x")
        self.invalid({"op": "printf"},
                     {"op": "printf", "format": "%s scored %d\\n", "arguments": ["alice"]},
                     {"op": "printf", "format": "%d\\n", "arguments": ["abc"]},
                     {"op": "printf", "format": "%x\\n", "arguments": ["1"]},
                     {"op": "printf", "format": "%.2f\\n", "arguments": ["2.675"]},  # rounding tie
                     {"op": "printf", "format": "%f\\n", "arguments": ["1e5"]},
                     {"op": "printf", "format": "%05s\\n", "arguments": ["x"]},
                     {"op": "printf", "format": "%.2d\\n", "arguments": ["1"]},
                     {"op": "printf", "format": "plain\\n", "arguments": ["extra"]})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "printf", "format": "%s\\n", "arguments": ["alpha", "beta", "gamma"]}, "printf '%s\\n' alpha beta gamma",
                   good=["echo alpha; echo beta; echo gamma"], bad=["echo alpha beta gamma", "printf '%s\\n' alpha gamma beta"])
        self.check({"op": "printf", "format": "%s\\t%s\\n", "arguments": ["name", "score", "alice", "42"]},
                   "printf '%s\\t%s\\n' name score alice 42", good=["printf 'name\\tscore\\nalice\\t42\\n'"],
                   bad=["printf '%s %s\\n' name score alice 42"])
        self.check({"op": "printf", "format": "%03d\\n", "arguments": ["7"]}, "printf '%03d\\n' 7",
                   good=["echo 007"], bad=["printf '%d\\n' 7", "printf '%04d\\n' 7"])
        self.check({"op": "printf", "format": "%.2f\\n", "arguments": ["3.14159"]}, "printf '%.2f\\n' 3.14159",
                   good=["echo 3.14"], bad=["printf '%.3f\\n' 3.14159", "printf '%.2f' 3.14159"])

    def test_oracle_formatting_matches_real_printf(self):
        self.check({"op": "printf", "format": "%.2f\\n", "arguments": ["19.999"]}, "printf '%.2f\\n' 19.999", bad=["echo 19.99"])
        self.check({"op": "printf", "format": "%.1f\\n", "arguments": ["0.26"]}, "printf '%.1f\\n' 0.26", bad=["echo 0.2"])
        self.check({"op": "printf", "format": "%f\\n", "arguments": ["1.5"]}, "printf '%f\\n' 1.5", good=["echo 1.500000"])
        self.check({"op": "printf", "format": "%-6s|%5s\\n", "arguments": ["name", "42"]}, "printf '%-6s|%5s\\n' name 42",
                   good=["echo 'name  |   42'"])
        self.check({"op": "printf", "format": "%05d\\n", "arguments": ["-42"]}, "printf '%05d\\n' -42",
                   good=["printf '%s\\n' -0042"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "printf")


class SeqTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "seq", "first": 1, "step": 2, "last": 9}), "seq 1 2 9")
        self.assertEqual(render({"op": "seq", "first": 1, "last": 3, "separator": " "}), "seq -s ' ' 1 3")
        self.invalid({"op": "seq"}, {"op": "seq", "step": 2, "last": 9}, {"op": "seq", "first": 9, "last": 1},
                     {"op": "seq", "first": 1, "step": 0, "last": 9}, {"op": "seq", "last": 5, "separator": "\\"},
                     {"op": "seq", "last": 5, "separator": "-"})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "seq", "first": 1, "step": 2, "last": 9}, "seq 1 2 9", good=["seq 1 2 10"], bad=["seq 1 9", "seq 2 2 10"])
        self.check({"op": "seq", "last": 5}, "seq 5", good=["seq 1 5"], bad=["seq 4", "seq 0 5"])
        self.check({"op": "seq", "first": 1, "last": 5, "separator": ","}, "seq -s , 1 5",
                   good=["seq 1 5 | paste -sd,"], bad=["seq 1 5", "seq -s ', ' 1 5"])
        self.check({"op": "seq", "first": 8, "last": 12, "equal_width": True}, "seq -w 8 12",
                   good=["printf '%02d\\n' 8 9 10 11 12"], bad=["seq 8 12"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "seq")


class ExprTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "expr", "left": 17, "operator": "%", "right": 5}), "expr 17 % 5")
        self.invalid({"op": "expr"}, {"op": "expr", "left": 6, "operator": "*"}, {"op": "expr", "left": 6, "operator": "^", "right": 7},
                     {"op": "expr", "left": 3, "operator": "-", "right": 3}, {"op": "expr", "left": 3, "operator": "/", "right": 0},
                     {"op": "expr", "left": 1, "operator": ">", "right": 2}, {"op": "expr", "length_of": "hello", "left": 1},
                     {"op": "expr", "length_of": "-x"}, {"op": "expr", "substr_of": "abc", "start": 0, "count": 1},
                     {"op": "expr", "substr_of": "a0b", "start": 2, "count": 1})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "expr", "left": 6, "operator": "*", "right": 7}, "expr 6 '*' 7",
                   good=["expr 6 \\* 7", "echo $((6 * 7))"], bad=["expr 6 + 7", "expr 7 '*' 7"])
        self.check({"op": "expr", "left": 100, "operator": "/", "right": 8}, "expr 100 / 8",
                   good=["echo $((100 / 8))"], bad=["expr 100 % 8"])
        self.check({"op": "expr", "length_of": "hello world"}, "expr length 'hello world'",
                   good=["expr 'hello world' : '.*'"], bad=["expr length hello"])
        self.check({"op": "expr", "substr_of": "release candidate", "start": 1, "count": 7}, "expr substr 'release candidate' 1 7",
                   good=["echo release"], bad=["expr substr 'release candidate' 2 7"])
        self.check({"op": "expr", "left": 15, "operator": ">", "right": 9}, "expr 15 '>' 9", bad=["expr 15 '<' 9"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "expr")


class FactorTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "factor", "number": 12, "others": [35, 100]}), "factor 12 35 100")
        self.invalid({"op": "factor"}, {"op": "factor", "number": 1}, {"op": "factor", "number": True},
                     {"op": "factor", "number": 12, "others": [1]})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "factor", "number": 360}, "factor 360", good=["factor $((180 * 2))"], bad=["factor 84", "echo 360"])
        self.check({"op": "factor", "number": 97}, "factor 97", good=["echo '97: 97'"], bad=["factor 91"])
        self.check({"op": "factor", "number": 12, "others": [35, 100]}, "factor 12 35 100",
                   good=["factor 12; factor 35; factor 100"], bad=["factor 12 35", "factor 100 35 12"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "factor")


class TrueTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "true"}), "true")
        self.invalid({"op": "true", "variant": "colon"}, {"op": "true", "arguments": ["x"]})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "true"}, "true", good=[":", "/bin/true"], bad=["false", "echo ok"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "true")


class FalseTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "false"}), "false")
        self.invalid({"op": "false", "variant": "path"}, {"op": "false", "bogus": True})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "false"}, "false", good=["/bin/false", "! true"], bad=["true", "(exit 2)", "echo failed; false"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "false")


class TestCommandTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "test", "condition": "directory", "target": "my logs"}), "test -d 'my logs'")
        self.invalid({"op": "test", "condition": "file"}, {"op": "test", "condition": "bogus", "target": "notes.txt"},
                     {"op": "test", "target": "notes.txt"}, {"op": "test", "condition": "number_lt", "left": "a", "right": "3"},
                     {"op": "test", "condition": "string_equal", "left": "-n", "right": "x"},
                     {"op": "test", "condition": "string_equal", "left": "x", "right": "x", "target": "f"},
                     {"op": "test", "condition": "number_lt", "left": "1"})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "test", "condition": "file", "target": "notes.txt"}, "test -f notes.txt",
                   good=["[ -f notes.txt ]"], bad=["test -d notes.txt", "test -f other.txt"])
        self.check({"op": "test", "condition": "string_differs", "left": "red apple", "right": "green pear"},
                   "test 'red apple' != 'green pear'", good=["[ 'red apple' != 'green pear' ]"],
                   bad=["test 'red apple' = 'green pear'"])
        self.check({"op": "test", "condition": "number_lt", "left": "12", "right": "30"}, "test 12 -lt 30",
                   good=["[ 12 -le 30 ]"], bad=["test 12 -gt 30"])
        self.check({"op": "test", "condition": "nonempty", "target": "report.csv"}, "test -s report.csv",
                   good=["[ -s report.csv ]"], bad=["test -s missing.csv"])
        self.check({"op": "test", "condition": "directory", "target": "zephyr"}, "test -d zephyr",
                   bad=["test -f zephyr", "test -d tundra"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "test")


class YesTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "yes", "text": "it's fine", "count": 4}), "yes \"it's fine\" | head -n 4")
        self.invalid({"op": "yes", "text": "ok"}, {"op": "yes", "text": "ok", "count": 0}, {"op": "yes", "text": "-n", "count": 3},
                     {"op": "yes", "text": "y", "count": 3})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "yes", "text": "ok", "count": 3}, "yes ok | head -n 3",
                   good=["printf 'ok\\nok\\nok\\n'"], bad=["yes ok | head -n 2", "yes no | head -n 3"])
        self.check({"op": "yes", "count": 5}, "yes | head -n 5", good=["yes y | head -n 5"], bad=["yes | head -n 4"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "yes")


class SleepTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "sleep", "duration": "0.25"}), "sleep 0.25")
        self.invalid({"op": "sleep"}, {"op": "sleep", "seconds": 3}, {"op": "sleep", "seconds": 0},
                     {"op": "sleep", "duration": "1.0"}, {"op": "sleep", "duration": ".5"}, {"op": "sleep", "duration": "0.50"},
                     {"op": "sleep", "duration": "0.5s"}, {"op": "sleep", "duration": "2.5"},
                     {"op": "sleep", "seconds": 1, "duration": "0.5"})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "sleep", "seconds": 1}, "sleep 1", good=["sleep 1s"], bad=["sleep 5", "echo done"])  # 5 s exceeds the limit
        self.check({"op": "sleep", "duration": "0.5"}, "sleep 0.5", good=["sleep .5"], bad=["sleep 4"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "sleep")


class TimeoutTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "timeout", "duration": "0.5", "sleep_seconds": 3}), "timeout 0.5 sleep 3")
        self.invalid({"op": "timeout", "seconds": 1}, {"op": "timeout", "seconds": 1, "duration": "0.5", "sleep_seconds": 5},
                     {"op": "timeout", "duration": "0.50", "sleep_seconds": 3}, {"op": "timeout", "seconds": 3, "sleep_seconds": 5},
                     {"op": "timeout", "seconds": 1, "sleep_seconds": 1}, {"op": "timeout", "seconds": 1, "sleep_seconds": 5, "follow": "app.log"},
                     {"op": "timeout", "seconds": 1, "follow": "-app.log"}, {"op": "timeout", "seconds": 1, "sleep_seconds": 5, "signal": "KILL"})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "timeout", "seconds": 1, "sleep_seconds": 5}, "timeout 1 sleep 5",
                   good=["timeout 1s sleep 9"], bad=["sleep 5", "timeout 1 true"])
        self.check({"op": "timeout", "seconds": 1, "follow": "app.log"}, "timeout 1 tail -f app.log",
                   good=["timeout 1 tail -n 10 -f app.log"], bad=["tail -n 10 app.log", "timeout 1 tail -n 3 -f app.log"])
        self.check({"op": "timeout", "seconds": 1, "sleep_seconds": 20, "signal": "HUP"}, "timeout -s HUP 1 sleep 20",
                   good=["timeout --signal=HUP 1 sleep 20"], bad=["timeout 2 sleep 1"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "timeout")


class EnvTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "env"}), "env")
        self.assertEqual(render({"op": "env", "assignments": ["NOTE=hello world"], "show": ["NOTE"]}), "env NOTE='hello world' printenv NOTE")
        self.invalid({"op": "env", "clean": True}, {"op": "env", "show": ["A"]}, {"op": "env", "assignments": ["A=1"]},
                     {"op": "env", "assignments": ["A=1"], "show": ["B"]}, {"op": "env", "assignments": ["A=1"], "clean": True, "show": ["A"]},
                     {"op": "env", "unset": "NOPE"}, {"op": "env", "unset": "HOME", "assignments": ["A=1"], "show": ["A"]},
                     {"op": "env", "assignments": ["PATH=x"], "show": ["PATH"]}, {"op": "env", "assignments": ["A=1", "A=2"], "show": ["A"]},
                     {"op": "env", "assignments": ["1A=1"], "show": ["1A"]}, {"op": "env", "chdir": "projects"})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "env"}, "env", good=["printenv"], bad=["printenv HOME", "env -u HOME printenv"])
        self.check({"op": "env", "assignments": ["MODE=test"], "show": ["MODE"]}, "env MODE=test printenv MODE",
                   good=["MODE=test printenv MODE"], bad=["env MODE=prod printenv MODE", "printenv MODE"])
        self.check({"op": "env", "assignments": ["GREETING=hello world"], "clean": True}, "env -i GREETING='hello world' printenv",
                   good=["env -i GREETING='hello world' env"], bad=["env GREETING='hello world' printenv", "env -i GREETING=hello printenv"])
        self.check({"op": "env", "unset": "HOME"}, "env -u HOME printenv", good=["(unset HOME; printenv)"],
                   bad=["printenv", "env -u TZ printenv"])
        self.check({"op": "env", "assignments": ["TUNDRA=cold", "ZEPHYR=wind"], "show": ["TUNDRA", "ZEPHYR"]},
                   "env TUNDRA=cold ZEPHYR=wind printenv TUNDRA ZEPHYR", good=["TUNDRA=cold ZEPHYR=wind printenv TUNDRA ZEPHYR"],
                   bad=["env TUNDRA=cold ZEPHYR=wind printenv ZEPHYR TUNDRA"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "env")


class PrintenvTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "printenv", "names": ["LANG", "LC_ALL"]}), "printenv LANG LC_ALL")
        self.invalid({"op": "printenv"}, {"op": "printenv", "names": ["MODE"]}, {"op": "printenv", "names": ["PWD"]},
                     {"op": "printenv", "variable": "HOME"}, {"op": "printenv", "names": ["HOME", "HOME"]})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "printenv", "names": ["HOME"]}, "printenv HOME", good=['echo "$HOME"'], bad=["printenv PATH", "echo /home"])
        self.check({"op": "printenv", "names": ["LANG", "LC_ALL"]}, "printenv LANG LC_ALL", bad=["printenv LANG"])
        self.check({"op": "printenv", "names": ["TERM"]}, "printenv TERM", good=['echo "$TERM"'], bad=["printenv TZ"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "printenv")


class WhoamiTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "whoami"}), "whoami")
        self.invalid({"op": "whoami", "transform": "upper"}, {"op": "whoami", "user": "root"})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "whoami"}, "whoami", good=["id -un"], bad=["echo root", "id"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "whoami")


class IdTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "id", "user": "root"}), "id root")
        self.assertEqual(render({"op": "id", "option": "u", "user": "root"}), "id -u root")
        self.invalid({"op": "id", "option": "un"}, {"op": "id", "user": "shellm"}, {"op": "id", "user": "nobody-here"},
                     {"op": "id", "bogus": True})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "id"}, "id", bad=["id -u", "whoami"])
        self.check({"op": "id", "option": "u"}, "id -u", good=["id -ru"], bad=["id -un", "id"])
        self.check({"op": "id", "option": "G"}, "id -G", bad=["id -Gn"])
        self.check({"op": "id", "option": "u", "user": "root"}, "id -u root", good=["echo 0"], bad=["id -u"])
        self.check({"op": "id", "user": "root"}, "id root", bad=["id"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "id")


class GroupsTests(ShellUtilCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "groups", "user": "root"}), "groups root")
        self.invalid({"op": "groups", "user": "shellm"}, {"op": "groups", "user": "nobody-here"}, {"op": "groups", "transform": "upper"})

    def test_equivalent_and_wrong_commands(self):
        self.check({"op": "groups"}, "groups", good=["id -Gn"], bad=["id -g", "groups root"])
        self.check({"op": "groups", "user": "root"}, "groups root", bad=["groups"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("shell-utils", "groups")


if __name__ == "__main__":
    unittest.main()
