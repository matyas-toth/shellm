"""Text and stream command families: render, validation, and Docker-backed oracle behavior."""

import unittest

from shellbench.sandbox import run_container
from shellm_data.intents import check_intent, make_fixture, render, validate_intent

try:
    from .utility_helpers import UtilityCase
except ImportError:
    from utility_helpers import UtilityCase


class BatchCase(UtilityCase):
    def verdicts(self, intent, commands):
        """Run every command on both fixtures in one container; map command -> accepted by the oracle."""
        fixtures = [make_fixture(intent, seed) for seed in (0, 1)]
        items = [{"id": str(index), "command": command, "fixtures": fixtures} for index, command in enumerate(commands)]
        results = run_container(self.cli, self.image, items, [make_fixture({"op": "pwd"}, 0)] * 2)
        verdict = {}
        for index, command in enumerate(commands):
            try:
                for spec, outcome in zip(fixtures, results[str(index)], strict=True):
                    check_intent(intent, spec, outcome)
                verdict[command] = True
            except ValueError:
                verdict[command] = False
        return verdict

    def assert_verdicts(self, intent, accept=(), reject=()):
        verdict = self.verdicts(intent, [*accept, *reject])
        for command in accept:
            self.assertTrue(verdict[command], f"should be accepted: {command}")
        for command in reject:
            self.assertFalse(verdict[command], f"should be rejected: {command}")


class SortTests(BatchCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "sort", "source": "names.txt", "reverse": True, "unique": True}), "sort -ru names.txt")
        for invalid in ({"op": "sort", "source": "names.txt", "bogus": True}, {"op": "sort"},
                        {"op": "sort", "source": "a.csv", "key": 2}, {"op": "sort", "source": "a.csv", "key": 0, "delimiter": ","},
                        {"op": "sort", "source": "a.csv", "key": 2, "delimiter": ",", "unique": True}):
            with self.assertRaises(ValueError, msg=str(invalid)):
                validate_intent(invalid)

    def test_equivalent_and_wrong_commands(self):
        self.assert_verdicts({"op": "sort", "source": "names.txt", "reverse": True},
                             ["sort -r names.txt", "sort names.txt | tac"], ["sort names.txt", "sort -ru names.txt"])
        self.assert_verdicts({"op": "sort", "source": "numbers.txt", "numeric": True},
                             ["sort -n numbers.txt", "sort --numeric-sort numbers.txt"], ["sort numbers.txt"])
        self.assert_verdicts({"op": "sort", "source": "colors list.txt", "unique": True},
                             ["sort -u 'colors list.txt'", "sort 'colors list.txt' | uniq"], ["sort 'colors list.txt'"])

    def test_key_sorting(self):
        intent = {"op": "sort", "source": "scores.csv", "key": 2, "delimiter": ",", "numeric": True}
        self.assertEqual(render(intent), "sort -t, -k2,2 -n scores.csv")
        self.assert_verdicts(intent, ["sort -t, -k2,2 -n scores.csv", "sort -t, -k2n scores.csv"],
                             ["sort -t, -k2,2 scores.csv", "sort -n scores.csv", "sort -t, -k3,3 -n scores.csv"])
        reverse = {"op": "sort", "source": "tundra-scores.csv", "key": 2, "delimiter": ",", "numeric": True, "reverse": True}
        self.assertEqual(render(reverse), "sort -t, -k2,2 -rn tundra-scores.csv")
        self.assert_verdicts(reverse, ["sort -t, -k2,2 -rn tundra-scores.csv", "sort -t, -k2,2 -n tundra-scores.csv | tac"],
                             ["sort -t, -k2,2 -n tundra-scores.csv", "sort -t, -k2,2 -r tundra-scores.csv"])
        text = {"op": "sort", "source": "cities.csv", "key": 3, "delimiter": ","}
        self.assert_verdicts(text, ["sort -t, -k3,3 cities.csv"], ["sort -t, -k2,2 cities.csv", "sort cities.csv"])

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("text", "sort")


def more(intent, command, accept=(), reject=()):
    return dict(intent=intent, command=command, accept=list(accept), reject=list(reject))


# command -> the catalog intent, its canonical command, invalid intents, equivalent commands (accepted),
# wrong commands (rejected), further intents that must render exactly as given ("more"), and variants.
CASES = {
    "awk": dict(
        intent={"op": "awk", "source": "people.txt", "field": 2},
        command="awk '{print $2}' people.txt",
        invalid=[{"op": "awk", "source": "people.txt", "field": 0}, {"op": "awk", "source": "people.txt", "delimiter": ","},
                 {"op": "awk", "source": "people.csv", "field": 2, "delimiter": ","},
                 {"op": "awk", "source": "a.txt", "sum_field": 2, "field": 1}, {"op": "awk", "source": "a.txt", "where_field": 2, "field": 1},
                 {"op": "awk", "source": "a.txt", "where_field": 2, "where_value": 'a"b'}],
        accept=["awk '{ print $2 }' people.txt", "awk '{print $2}' < people.txt"],
        reject=["cut -d' ' -f2 people.txt", "awk '{print $1}' people.txt", "awk -F'\\t' '{print $2}' people.txt"],
        more=[more({"op": "awk", "source": "people.txt", "field": 1}, "awk '{print $1}' people.txt", [], ["cut -d' ' -f1 people.txt"]),
              more({"op": "awk", "source": "orders.txt", "where_field": 3, "where_value": "shipped", "field": 1},
                   "awk '$3 == \"shipped\" {print $1}' orders.txt",
                   ["awk '$3==\"shipped\"{print $1}' orders.txt"],
                   ["awk '$3 == \"shipped\"' orders.txt", "awk '$2 == \"shipped\" {print $1}' orders.txt"]),
              more({"op": "awk", "source": "expenses.txt", "sum_field": 2}, "awk '{s+=$2} END {print s}' expenses.txt",
                   ["awk '{t+=$2} END{print t}' expenses.txt"], ["awk '{s+=$3} END {print s}' expenses.txt", "awk 'END {print NR}' expenses.txt"]),
              more({"op": "awk", "source": "expenses.csv", "sum_field": 3, "delimiter": ","}, "awk -F, '{s+=$3} END {print s}' expenses.csv",
                   [], ["awk '{s+=$3} END {print s}' expenses.csv"]),
              more({"op": "awk", "source": "passwd copy.txt", "delimiter": ":", "where_field": 7, "where_value": "/bin/bash", "field": 1},
                   "awk -F: '$7 == \"/bin/bash\" {print $1}' 'passwd copy.txt'",
                   ["awk -F: '$7==\"/bin/bash\"{print $1}' 'passwd copy.txt'"], ["awk '$7 == \"/bin/bash\" {print $1}' 'passwd copy.txt'"]),
              more({"op": "awk", "source": "zephyr-orders.txt", "where_field": 2, "where_value": "open"}, "awk '$2 == \"open\"' zephyr-orders.txt",
                   [], ["awk '$2 == \"open\" {print $1}' zephyr-orders.txt", "awk '$3 == \"open\"' zephyr-orders.txt"])]),
    "sed": dict(
        intent={"op": "sed", "source": "app.log", "pattern": "error", "replacement": "warning", "global": False},
        command="sed 's/error/warning/' app.log",
        invalid=[{"op": "sed", "source": "app.log", "pattern": "a/b", "replacement": "c"}, {"op": "sed", "source": "app.log", "pattern": "x"},
                 {"op": "sed", "source": "app.log", "pattern": "it's", "replacement": "x"},
                 {"op": "sed", "source": "a.txt", "delete": "x"}, {"op": "sed", "source": "a.txt", "delete_prefix": "#", "start": 1},
                 {"op": "sed", "source": "a.txt", "start": 3, "end": 2}, {"op": "sed", "source": "a.txt", "start": 1, "in_place": True},
                 {"op": "sed", "source": "a.txt", "delete_prefix": "#", "global": True}],
        accept=["sed 's/error/warning/1' app.log", "sed s/error/warning/ app.log"],
        reject=["sed 's/error/warning/g' app.log", "sed -i 's/error/warning/' app.log"],
        more=[more({"op": "sed", "source": "app.log", "pattern": "error", "replacement": "warning", "global": True}, "sed 's/error/warning/g' app.log"),
              more({"op": "sed", "source": "my notes.txt", "pattern": "colour", "replacement": "color", "global": True, "in_place": True},
                   "sed -i 's/colour/color/g' 'my notes.txt'", ["sed --in-place 's/colour/color/g' 'my notes.txt'"],
                   ["sed 's/colour/color/g' 'my notes.txt'", "sed -i 's/colour/color/' 'my notes.txt'"]),
              more({"op": "sed", "source": "settings.conf", "delete_prefix": "#"}, "sed '/^#/d' settings.conf",
                   ["grep -v '^#' settings.conf"], ["sed '/#/d' settings.conf", "grep -v '#' settings.conf", "sed '/^ *#/d' settings.conf"]),
              more({"op": "sed", "source": "chapters.txt", "start": 3, "end": 5}, "sed -n '3,5p' chapters.txt",
                   ["head -n 5 chapters.txt | tail -n 3"], ["sed -n '3,4p' chapters.txt", "sed '3,5d' chapters.txt"]),
              more({"op": "sed", "source": "chapters.txt", "start": 4}, "sed -n '4p' chapters.txt", [], ["sed -n '5p' chapters.txt"])]),
    "uniq": dict(
        intent={"op": "uniq", "source": "visits.txt", "count": True},
        command="uniq -c visits.txt",
        invalid=[{"op": "uniq", "source": "visits.txt", "count": "yes"}, {"op": "uniq", "count": True},
                 {"op": "uniq", "source": "v.txt", "duplicates": True, "unique": True}],
        accept=["uniq --count visits.txt"],
        reject=["sort visits.txt | uniq -c", "uniq visits.txt"],
        more=[more({"op": "uniq", "source": "visits.txt"}, "uniq visits.txt"),
              more({"op": "uniq", "source": "tag list.txt"}, "uniq 'tag list.txt'", ["uniq < 'tag list.txt'"], ["sort -u 'tag list.txt'", "cat 'tag list.txt'"]),
              more({"op": "uniq", "source": "error codes.txt", "duplicates": True}, "uniq -d 'error codes.txt'",
                   ["uniq --repeated 'error codes.txt'"], ["uniq -u 'error codes.txt'", "uniq 'error codes.txt'"]),
              more({"op": "uniq", "source": "ids.txt", "unique": True}, "uniq -u ids.txt", ["uniq --unique ids.txt"], ["uniq -d ids.txt"]),
              more({"op": "uniq", "source": "tundra-visits.txt", "count": True, "duplicates": True}, "uniq -cd tundra-visits.txt",
                   ["uniq -dc tundra-visits.txt"], ["uniq -d tundra-visits.txt", "uniq -c tundra-visits.txt"])]),
    "cut": dict(
        intent={"op": "cut", "source": "accounts.txt", "delimiter": ":", "fields": [1, 3]},
        command="cut -d: -f1,3 accounts.txt",
        invalid=[{"op": "cut", "source": "accounts.txt", "delimiter": ":", "fields": [3, 1]},
                 {"op": "cut", "source": "accounts.txt", "delimiter": "::", "fields": [1]},
                 {"op": "cut", "source": "a.txt", "characters": "5-2"}, {"op": "cut", "source": "a.txt", "characters": "1-4", "fields": [1]}],
        accept=["cut -d : -f 1,3 accounts.txt", "cut --delimiter=: --fields=1,3 accounts.txt"],
        reject=["cut -d: -f1,2 accounts.txt", "cut -d: -f1 accounts.txt"],
        more=[more({"op": "cut", "source": "dates.txt", "characters": "1-4"}, "cut -c1-4 dates.txt",
                   ["cut --characters=1-4 dates.txt"], ["cut -c1-3 dates.txt", "cut -c2-4 dates.txt"]),
              more({"op": "cut", "source": "dates.txt", "characters": "6"}, "cut -c6 dates.txt", [], ["cut -c5 dates.txt"]),
              more({"op": "cut", "source": "sales data.csv", "delimiter": ",", "fields": [1, 3, 4]}, "cut -d, -f1,3,4 'sales data.csv'",
                   ["cut -d ',' -f 1,3,4 'sales data.csv'"], ["cut -d, -f1-4 'sales data.csv'"]),
              more({"op": "cut", "source": "report.tsv", "fields": [2]}, "cut -f2 report.tsv",
                   ["cut -d$'\\t' -f2 report.tsv"], ["cut -d' ' -f2 report.tsv", "cut -f1 report.tsv"]),
              more({"op": "cut", "source": "zephyr entries.csv", "delimiter": "|", "fields": [2, 3]}, "cut -d'|' -f2,3 'zephyr entries.csv'",
                   [], ["cut -d, -f2,3 'zephyr entries.csv'"])]),
    "tr": dict(
        intent={"op": "tr", "source": "notes.txt", "from": "a-z", "to": "A-Z"},
        command="tr a-z A-Z < notes.txt",
        invalid=[{"op": "tr", "source": "notes.txt", "from": "a-z", "to": "A-Y"}, {"op": "tr", "source": "notes.txt", "from": "a-z"},
                 {"op": "tr", "source": "notes.txt", "from": "a-z", "to": "A-Z", "delete": True},
                 {"op": "tr", "source": "notes.txt", "from": "ab", "delete": True, "squeeze": True}],
        accept=["tr '[:lower:]' '[:upper:]' < notes.txt", "cat notes.txt | tr a-z A-Z"],
        reject=["tr A-Z a-z < notes.txt", "tr -d a-z < notes.txt"],
        more=[more({"op": "tr", "source": "vowel text.txt", "from": "aeiou", "delete": True}, "tr -d aeiou < 'vowel text.txt'",
                    ["tr -d '[aeiou]' < 'vowel text.txt'"], ["tr -d AEIOU < 'vowel text.txt'", "tr aeiou AEIOU < 'vowel text.txt'"]),
              more({"op": "tr", "source": "shout.txt", "from": "A-Z", "to": "a-z"}, "tr A-Z a-z < shout.txt",
                   ["tr '[:upper:]' '[:lower:]' < shout.txt"], ["tr a-z A-Z < shout.txt"]),
              more({"op": "tr", "source": "spaced out.txt", "from": " ", "squeeze": True}, "tr -s ' ' < 'spaced out.txt'",
                   ["cat 'spaced out.txt' | tr -s ' '"], ["tr -d ' ' < 'spaced out.txt'", "tr -s a-z < 'spaced out.txt'"]),
              more({"op": "tr", "source": "zephyr-secret.txt", "from": "a-zA-Z", "to": "n-za-mN-ZA-M"}, "tr a-zA-Z n-za-mN-ZA-M < zephyr-secret.txt",
                   ["tr 'A-Za-z' 'N-ZA-Mn-za-m' < zephyr-secret.txt"], ["tr a-z n-za-m < zephyr-secret.txt"])]),
    "paste": dict(
        intent={"op": "paste", "sources": ["names.txt", "scores.txt"], "delimiter": ","},
        command="paste -d, names.txt scores.txt",
        invalid=[{"op": "paste", "sources": ["names.txt"]}, {"op": "paste", "sources": ["a.txt", "b.txt"], "delimiter": ", "}],
        accept=["paste -d ',' names.txt scores.txt"],
        reject=["paste names.txt scores.txt", "paste -d, scores.txt names.txt"],
        more=[more({"op": "paste", "sources": ["first names.txt", "last names.txt"]}, "paste 'first names.txt' 'last names.txt'",
                   [], ["paste -d, 'first names.txt' 'last names.txt'", "paste 'last names.txt' 'first names.txt'"]),
              more({"op": "paste", "sources": ["items.txt"], "serial": True, "delimiter": ","}, "paste -s -d, items.txt",
                   ["paste -sd, items.txt", "paste -d, -s items.txt"], ["paste -d, items.txt", "paste -s items.txt"]),
              more({"op": "paste", "sources": ["a col.txt", "b col.txt", "c col.txt"], "delimiter": ":"}, "paste -d: 'a col.txt' 'b col.txt' 'c col.txt'",
                   [], ["paste -d: 'a col.txt' 'b col.txt'", "paste 'a col.txt' 'b col.txt' 'c col.txt'"]),
              more({"op": "paste", "sources": ["tundra-a.txt", "zephyr-b.txt"], "serial": True, "delimiter": ":"}, "paste -s -d: tundra-a.txt zephyr-b.txt",
                   [], ["paste -d: tundra-a.txt zephyr-b.txt"])]),
    "nl": dict(
        intent={"op": "nl", "source": "poem.txt"},
        command="nl poem.txt",
        invalid=[{"op": "nl", "source": "poem.txt", "width": 0}, {"op": "nl"}, {"op": "nl", "source": "poem.txt", "bogus": 3},
                 {"op": "nl", "source": "poem.txt", "separator": "a\\b"}],
        accept=["nl -b t poem.txt", "nl < poem.txt"],
        reject=["nl -ba poem.txt", "cat poem.txt"],
        more=[more({"op": "nl", "source": "todo list.txt", "all": True}, "nl -b a 'todo list.txt'", ["nl -ba 'todo list.txt'"], ["nl 'todo list.txt'"]),
              more({"op": "nl", "source": "code.txt", "separator": ": "}, "nl -s ': ' code.txt", ["nl -s': ' code.txt"], ["nl code.txt", "nl -s ':' code.txt"]),
              more({"op": "nl", "source": "menu.txt", "width": 3, "start": 10}, "nl -w 3 -v 10 menu.txt", ["nl -v10 -w3 menu.txt"],
                   ["nl -w 3 menu.txt", "nl -v 10 menu.txt"]),
              more({"op": "nl", "source": "tundra poem.txt", "all": True, "separator": " | "}, "nl -b a -s ' | ' 'tundra poem.txt'",
                   [], ["nl -b a 'tundra poem.txt'", "nl -s ' | ' 'tundra poem.txt'"])]),
    "tac": dict(
        intent={"op": "tac", "source": "history.txt"},
        command="tac history.txt",
        invalid=[{"op": "tac"}, {"op": "tac", "source": ""}, {"op": "tac", "source": "a.txt", "sources": ["b.txt"]}],
        accept=["tac < history.txt"],
        reject=["cat history.txt", "sort -r history.txt"],
        more=[more({"op": "tac", "source": "my history.txt"}, "tac 'my history.txt'", [], ["cat 'my history.txt'"]),
              more({"op": "tac", "source": "-oldest.txt"}, "tac -- -oldest.txt", ["tac ./-oldest.txt"], ["cat -- -oldest.txt"]),
              more({"op": "tac", "sources": ["part1.txt", "part2.txt"]}, "tac part1.txt part2.txt", ["tac part1.txt; tac part2.txt"],
                   ["cat part1.txt part2.txt | tac", "tac part2.txt part1.txt"]),
              more({"op": "tac", "source": "zephyr/tundra queue.txt"}, "tac 'zephyr/tundra queue.txt'", [], ["cat 'zephyr/tundra queue.txt'"])]),
    "rev": dict(
        intent={"op": "rev", "source": "words.txt"},
        command="rev words.txt",
        invalid=[{"op": "rev"}, {"op": "rev", "source": "words.txt", "bogus": True}],
        accept=["rev < words.txt"],
        reject=["tac words.txt", "cat words.txt"],
        more=[more({"op": "rev", "source": "my words.txt"}, "rev 'my words.txt'", [], ["tac 'my words.txt'"]),
              more({"op": "rev", "source": "-names.txt"}, "rev -- -names.txt", ["rev ./-names.txt"], ["cat -- -names.txt"]),
              more({"op": "rev", "sources": ["list1.txt", "list2.txt"]}, "rev list1.txt list2.txt", ["rev list1.txt; rev list2.txt"],
                   ["rev list2.txt list1.txt", "rev list1.txt"]),
              more({"op": "rev", "source": "tundra/zephyr words.txt"}, "rev 'tundra/zephyr words.txt'", [], ["cat 'tundra/zephyr words.txt'"])]),
    "fold": dict(
        intent={"op": "fold", "source": "article.txt", "width": 30, "spaces": True},
        command="fold -s -w 30 article.txt",
        invalid=[{"op": "fold", "source": "article.txt", "width": 0}, {"op": "fold", "source": "article.txt", "width": -1}],
        accept=["fold -w 30 -s article.txt", "fold --spaces --width=30 article.txt"],
        reject=["fold -w 30 article.txt", "fold -s -w 20 article.txt"],
        more=[more({"op": "fold", "source": "article.txt", "width": 20}, "fold -w 20 article.txt", [], []),
              more({"op": "fold", "source": "long lines.txt", "width": 20}, "fold -w 20 'long lines.txt'",
                   ["fold -w20 'long lines.txt'", "fold --width=20 'long lines.txt'"], ["fold -s -w 20 'long lines.txt'", "fold -w 21 'long lines.txt'"]),
              more({"op": "fold", "source": "wide.txt"}, "fold wide.txt", ["fold -w 80 wide.txt"], ["fold -w 40 wide.txt", "fold -s wide.txt"]),
              more({"op": "fold", "source": "my article.txt", "width": 50, "spaces": True}, "fold -s -w 50 'my article.txt'",
                   [], ["fold -w 50 'my article.txt'"]),
              more({"op": "fold", "source": "tundra-report.txt", "width": 12}, "fold -w 12 tundra-report.txt", [], ["fold -s -w 12 tundra-report.txt"])]),
    "expand": dict(
        intent={"op": "expand", "source": "code.txt", "tabstop": 4},
        command="expand -t 4 code.txt",
        invalid=[{"op": "expand", "source": "code.txt", "tabstop": 0}, {"op": "expand", "source": "code.txt", "tabstop": "4"}],
        accept=["expand --tabs=4 code.txt"],
        reject=["expand code.txt", "expand -t 2 code.txt"],
        more=[more({"op": "expand", "source": "code.txt"}, "expand code.txt"),
              more({"op": "expand", "source": "Makefile snippet.txt"}, "expand 'Makefile snippet.txt'", ["expand -t 8 'Makefile snippet.txt'"],
                   ["expand -t 4 'Makefile snippet.txt'"]),
              more({"op": "expand", "source": "nested.txt", "initial": True, "tabstop": 4}, "expand -i -t 4 nested.txt",
                   ["expand --initial --tabs=4 nested.txt"], ["expand -t 4 nested.txt", "expand -i nested.txt"]),
              more({"op": "expand", "source": "-config.txt", "tabstop": 2}, "expand -t 2 -- -config.txt", ["expand -t 2 ./-config.txt"],
                   ["expand -t 4 ./-config.txt"]),
              more({"op": "expand", "source": "zephyr-table.txt", "tabstop": 10}, "expand -t 10 zephyr-table.txt", [], ["expand zephyr-table.txt"])]),
    "unexpand": dict(
        intent={"op": "unexpand", "source": "indented.txt"},
        command="unexpand indented.txt",
        invalid=[{"op": "unexpand", "source": "indented.txt", "tabstop": 1}, {"op": "unexpand"},
                 {"op": "unexpand", "source": "a.txt", "all": True, "tabstop": 4}],
        accept=["unexpand --first-only indented.txt"],
        reject=["unexpand -a indented.txt", "cat indented.txt"],
        more=[more({"op": "unexpand", "source": "table.txt", "all": True}, "unexpand -a table.txt", ["unexpand --all table.txt"], ["unexpand table.txt"]),
              more({"op": "unexpand", "source": "code spaces.txt", "tabstop": 4}, "unexpand -t 4 'code spaces.txt'",
                   ["unexpand -a -t 4 'code spaces.txt'"], ["unexpand -a 'code spaces.txt'"]),
              more({"op": "unexpand", "source": "-spaced.txt"}, "unexpand -- -spaced.txt", ["unexpand ./-spaced.txt"], ["unexpand -a ./-spaced.txt"]),
              more({"op": "unexpand", "source": "tundra-table.txt", "all": True}, "unexpand -a tundra-table.txt", [], ["unexpand tundra-table.txt"])]),
    "comm": dict(
        intent={"op": "comm", "sources": ["list-a.txt", "list-b.txt"], "show": "common"},
        command="comm -12 list-a.txt list-b.txt",
        invalid=[{"op": "comm", "sources": ["list-a.txt", "list-b.txt"], "show": "both"},
                 {"op": "comm", "sources": ["list-a.txt"], "show": "common"}],
        accept=["comm -12 list-a.txt list-b.txt", "grep -Fxf list-a.txt list-b.txt"],
        reject=["comm -23 list-a.txt list-b.txt", "comm list-a.txt list-b.txt"],
        more=[more({"op": "comm", "sources": ["list-a.txt", "list-b.txt"], "show": "first_only"}, "comm -23 list-a.txt list-b.txt"),
              more({"op": "comm", "sources": ["list-a.txt", "list-b.txt"], "show": "second_only"}, "comm -13 list-a.txt list-b.txt"),
              more({"op": "comm", "sources": ["old list.txt", "new list.txt"], "show": "first_only"}, "comm -23 'old list.txt' 'new list.txt'",
                   ["grep -vxFf 'new list.txt' 'old list.txt'"], ["comm -13 'old list.txt' 'new list.txt'", "comm -12 'old list.txt' 'new list.txt'"]),
              more({"op": "comm", "sources": ["list-c.txt", "list-d.txt"], "show": "second_only"}, "comm -13 list-c.txt list-d.txt",
                   [], ["comm -23 list-c.txt list-d.txt"]),
              more({"op": "comm", "sources": ["set-a.txt", "set-b.txt"], "show": "all"}, "comm set-a.txt set-b.txt",
                   [], ["comm -3 set-a.txt set-b.txt", "comm -12 set-a.txt set-b.txt"]),
              more({"op": "comm", "sources": ["tundra-old.txt", "zephyr-new.txt"], "show": "first_only"}, "comm -23 tundra-old.txt zephyr-new.txt",
                   [], ["comm -13 tundra-old.txt zephyr-new.txt"])]),
    "od": dict(
        intent={"op": "od", "source": "data.bin", "format": "hex"},
        command="od -An -tx1 data.bin",
        invalid=[{"op": "od", "source": "data.bin", "format": "binary"}, {"op": "od", "source": "data.bin"}],
        accept=["od -An -t x1 data.bin"],
        reject=["od -An -tu1 data.bin", "od -tx1 data.bin"],
        more=[more({"op": "od", "source": "data.bin", "format": "decimal"}, "od -An -tu1 data.bin"),
              more({"op": "od", "source": "notes.bin", "format": "characters", "addresses": True}, "od -c notes.bin",
                   ["od --format=c notes.bin"], ["od -An -c notes.bin", "od -b notes.bin"]),
              more({"op": "od", "source": "my data.bin", "format": "octal"}, "od -An -to1 'my data.bin'",
                   ["od -An -b 'my data.bin'"], ["od -An -tx1 'my data.bin'", "od -to1 'my data.bin'"]),
              more({"op": "od", "source": "blob.bin", "format": "hex", "addresses": True}, "od -tx1 blob.bin",
                   ["od -t x1 blob.bin"], ["od -An -tx1 blob.bin"]),
              more({"op": "od", "source": "tundra.bin", "format": "characters"}, "od -An -c tundra.bin", [], ["od -c tundra.bin"])]),
    "split": dict(
        intent={"op": "split", "source": "big.txt", "lines": 3, "prefix": "part-"},
        command="split -l 3 big.txt part-",
        invalid=[{"op": "split", "source": "big.txt", "lines": 0, "prefix": "part-"},
                 {"op": "split", "source": "big.txt", "lines": 3, "prefix": "out/part-"},
                 {"op": "split", "source": "big.txt", "lines": 3, "bytes": 10}, {"op": "split", "source": "big.txt"}],
        accept=["split --lines=3 big.txt part-"],
        reject=["split -l 3 big.txt part_", "split -l 4 big.txt part-"],
        more=[more({"op": "split", "source": "big.txt", "lines": 4, "prefix": "chunk"}, "split -l 4 big.txt chunk"),
              more({"op": "split", "source": "data.txt", "bytes": 100, "prefix": "chunk-"}, "split -b 100 data.txt chunk-",
                   ["split --bytes=100 data.txt chunk-"], ["split -l 100 data.txt chunk-", "split -b 50 data.txt chunk-"]),
              more({"op": "split", "source": "big list.txt", "lines": 4}, "split -l 4 'big list.txt'", [], ["split -l 4 'big list.txt' part"]),
              more({"op": "split", "source": "records.txt", "lines": 5, "prefix": "rec_", "numeric_suffixes": True}, "split -l 5 -d records.txt rec_",
                   ["split -l 5 --numeric-suffixes records.txt rec_"], ["split -l 5 records.txt rec_"]),
              more({"op": "split", "source": "tundra.log", "bytes": 80, "prefix": "zephyr-"}, "split -b 80 tundra.log zephyr-",
                   [], ["split -b 80 tundra.log zephyr_"])]),
    "tee": dict(
        intent={"op": "tee", "source": "new.txt", "destination": "history.txt", "append": True},
        command="tee -a history.txt < new.txt",
        invalid=[{"op": "tee", "source": "same.txt", "destination": "same.txt"}, {"op": "tee", "source": "new.txt"},
                 {"op": "tee", "source": "n.txt", "destination": "a.txt", "destinations": ["b.txt"]}],
        accept=["cat new.txt | tee -a history.txt"],
        reject=["tee history.txt < new.txt", "cat new.txt >> history.txt"],
        more=[more({"op": "tee", "source": "new.txt", "destination": "copy.txt"}, "tee copy.txt < new.txt"),
              more({"op": "tee", "source": "draft text.txt", "destination": "backup copy.txt"}, "tee 'backup copy.txt' < 'draft text.txt'",
                   ["cat 'draft text.txt' | tee 'backup copy.txt'"], ["tee -a 'backup copy.txt' < 'draft text.txt'"]),
              more({"op": "tee", "source": "notes.txt", "destinations": ["out1.txt", "out2.txt"]}, "tee out1.txt out2.txt < notes.txt",
                   [], ["tee out1.txt < notes.txt", "tee -a out1.txt out2.txt < notes.txt"]),
              more({"op": "tee", "source": "entries.txt", "destination": "-log.txt", "append": True}, "tee -a -- -log.txt < entries.txt",
                   ["tee -a ./-log.txt < entries.txt"], ["tee -- -log.txt < entries.txt"]),
              more({"op": "tee", "source": "tundra-input.txt", "destinations": ["zephyr/a.txt", "zephyr/b.txt"], "append": True},
                   "tee -a zephyr/a.txt zephyr/b.txt < tundra-input.txt", [], ["tee zephyr/a.txt zephyr/b.txt < tundra-input.txt"])]),
    "xargs": dict(
        intent={"op": "xargs", "source": "stale.txt", "command": "rm"},
        command="xargs rm < stale.txt",
        invalid=[{"op": "xargs", "source": "stale.txt", "command": "ls"}, {"op": "xargs", "source": "stale.txt"},
                 {"op": "xargs", "source": "s.txt", "command": "echo"}, {"op": "xargs", "source": "s.txt", "command": "cp"},
                 {"op": "xargs", "source": "s.txt", "command": "rm", "suffix": ".bak"},
                 {"op": "xargs", "source": "s.txt", "command": "cp", "suffix": "/x"}],
        accept=["cat stale.txt | xargs rm", "rm $(cat stale.txt)"],
        reject=["xargs cat < stale.txt", "rm stale.txt"],
        more=[more({"op": "xargs", "source": "parts.txt", "command": "cat"}, "xargs cat < parts.txt",
                   ["cat $(cat parts.txt)"], ["cat parts.txt", "xargs rm < parts.txt"]),
              more({"op": "xargs", "source": "new files.txt", "command": "touch"}, "xargs touch < 'new files.txt'",
                   ["while read -r f; do touch \"$f\"; done < 'new files.txt'"], ["touch 'new files.txt'", "xargs mkdir < 'new files.txt'"]),
              more({"op": "xargs", "source": "important.txt", "command": "cp", "suffix": ".bak"}, "xargs -I {} cp {} {}.bak < important.txt",
                   ["while IFS= read -r f; do cp \"$f\" \"$f.bak\"; done < important.txt"],
                   ["for f in $(cat important.txt); do cp $f $f.bak; done", "xargs -I {} cp {} {}.orig < important.txt",
                    "xargs -I {} mv {} {}.bak < important.txt"]),
              more({"op": "xargs", "source": "tundra-files.txt", "command": "cp", "suffix": ".orig"}, "xargs -I {} cp {} {}.orig < tundra-files.txt",
                   [], ["xargs -I {} cp {} {}.bak < tundra-files.txt"])]),
    "iconv": dict(
        intent={"op": "iconv", "source": "latin.txt", "from": "ISO-8859-1", "to": "UTF-8"},
        command="iconv -f ISO-8859-1 -t UTF-8 latin.txt",
        invalid=[{"op": "iconv", "source": "latin.txt", "from": "UTF-8", "to": "UTF-8"},
                 {"op": "iconv", "source": "latin.txt", "from": "UTF-8", "to": "ASCII"},
                 {"op": "iconv", "source": "latin.txt", "from": "UTF-8", "to": "UTF-16LE"},
                 {"op": "iconv", "source": "latin.txt", "from": "UTF-8", "to": "ISO-8859-1", "output": "latin.txt"}],
        accept=["iconv -f latin1 -t utf8 latin.txt"],
        reject=["cat latin.txt", "iconv -f UTF-8 -t ISO-8859-1 latin.txt"],
        more=[more({"op": "iconv", "source": "latin.txt", "from": "UTF-8", "to": "ASCII", "discard": True}, "iconv -c -f UTF-8 -t ASCII latin.txt"),
              more({"op": "iconv", "source": "notes utf8.txt", "from": "UTF-8", "to": "ISO-8859-1", "output": "notes-latin1.txt"},
                   "iconv -f UTF-8 -t ISO-8859-1 -o notes-latin1.txt 'notes utf8.txt'",
                   ["iconv -f UTF-8 -t ISO-8859-1 'notes utf8.txt' > notes-latin1.txt"],
                   ["iconv -f UTF-8 -t ISO-8859-1 -o other.txt 'notes utf8.txt'", "cp 'notes utf8.txt' notes-latin1.txt"]),
              more({"op": "iconv", "source": "cafe menu.txt", "from": "UTF-8", "to": "ASCII", "discard": True}, "iconv -c -f UTF-8 -t ASCII 'cafe menu.txt'",
                   [], ["iconv -f UTF-8 -t ASCII//TRANSLIT 'cafe menu.txt'", "cat 'cafe menu.txt'"]),
              more({"op": "iconv", "source": "windows.txt", "from": "UTF-16LE", "to": "UTF-8"}, "iconv -f UTF-16LE -t UTF-8 windows.txt",
                   [], ["cat windows.txt", "iconv -f UTF-16BE -t UTF-8 windows.txt"]),
              more({"op": "iconv", "source": "tundra-latin.txt", "from": "ISO-8859-1", "to": "UTF-8", "output": "zephyr-utf8.txt"},
                   "iconv -f ISO-8859-1 -t UTF-8 -o zephyr-utf8.txt tundra-latin.txt", [], ["iconv -f ISO-8859-1 -t UTF-8 tundra-latin.txt"])]),
    "base64": dict(
        intent={"op": "base64", "source": "secret.txt"},
        command="base64 secret.txt",
        invalid=[{"op": "base64"}, {"op": "base64", "source": "secret.txt", "decode": True, "wrap": 20}],
        accept=["base64 < secret.txt", "cat secret.txt | base64"],
        reject=["base64 -w 0 secret.txt", "cat secret.txt"],
        more=[more({"op": "base64", "source": "encoded.b64", "decode": True}, "base64 -d encoded.b64", ["base64 --decode encoded.b64"], ["base64 encoded.b64"]),
              more({"op": "base64", "source": "token.txt", "wrap": 0}, "base64 -w 0 token.txt",
                   ["base64 --wrap=0 token.txt", "base64 token.txt | tr -d '\\n'"], ["base64 token.txt"]),
              more({"op": "base64", "source": "msg.txt", "wrap": 20}, "base64 -w 20 msg.txt", ["base64 --wrap=20 msg.txt"],
                   ["base64 -w 19 msg.txt", "base64 msg.txt"]),
              more({"op": "base64", "source": "tundra-data.b64", "decode": True}, "base64 -d tundra-data.b64", [], ["base64 tundra-data.b64"])]),
    "md5sum": dict(
        intent={"op": "md5sum", "sources": ["report.txt"]},
        command="md5sum report.txt",
        invalid=[{"op": "md5sum", "sources": []}, {"op": "md5sum", "sources": ["a.txt", "a.txt"]},
                 {"op": "md5sum", "sources": ["a.txt", "b.txt"], "check": True}],
        accept=["md5sum -- report.txt"],
        reject=["md5sum < report.txt", "sha1sum report.txt"],
        more=[more({"op": "md5sum", "sources": ["report.txt", "backup.txt"]}, "md5sum report.txt backup.txt"),
              more({"op": "md5sum", "sources": ["a draft.txt", "final copy.txt"]}, "md5sum 'a draft.txt' 'final copy.txt'",
                   [], ["md5sum 'final copy.txt' 'a draft.txt'"]),
              more({"op": "md5sum", "sources": ["checksums.md5"], "check": True}, "md5sum -c checksums.md5", ["md5sum --check checksums.md5"],
                   ["md5sum checksums.md5", "md5sum -c --quiet checksums.md5"]),
              more({"op": "md5sum", "sources": ["-draft v2.txt"]}, "md5sum -- '-draft v2.txt'", [], ["md5sum ./'-draft v2.txt'"]),
              more({"op": "md5sum", "sources": ["tundra-checksums.md5"], "check": True}, "md5sum -c tundra-checksums.md5", [], ["md5sum tundra-checksums.md5"])]),
    "sha1sum": dict(
        intent={"op": "sha1sum", "sources": ["backup.txt"]},
        command="sha1sum backup.txt",
        invalid=[{"op": "sha1sum"}, {"op": "sha1sum", "sources": "backup.txt"}],
        accept=["sha1sum -- backup.txt"],
        reject=["cat backup.txt | sha1sum", "sha256sum backup.txt"],
        more=[more({"op": "sha1sum", "sources": ["SHA1SUMS"], "check": True}, "sha1sum -c SHA1SUMS", ["sha1sum --check SHA1SUMS"],
                   ["sha1sum SHA1SUMS", "sha1sum -c --status SHA1SUMS"]),
              more({"op": "sha1sum", "sources": ["-backup copy.txt"]}, "sha1sum -- '-backup copy.txt'", [], ["sha256sum -- '-backup copy.txt'"]),
              more({"op": "sha1sum", "sources": ["src/main.txt", "docs/readme file.txt"]}, "sha1sum src/main.txt 'docs/readme file.txt'",
                   ["sha1sum src/main.txt; sha1sum 'docs/readme file.txt'"], ["sha1sum 'docs/readme file.txt' src/main.txt"]),
              more({"op": "sha1sum", "sources": ["tundra-archive.txt"]}, "sha1sum tundra-archive.txt", [], ["md5sum tundra-archive.txt"])]),
    "sha256sum": dict(
        intent={"op": "sha256sum", "sources": ["release.txt", "manifest.txt"]},
        command="sha256sum release.txt manifest.txt",
        invalid=[{"op": "sha256sum", "sources": ["a\\b.txt"]}, {"op": "sha256sum", "sources": ["a.txt"], "bogus": 1}],
        accept=["sha256sum release.txt && sha256sum manifest.txt"],
        reject=["sha256sum manifest.txt release.txt", "sha256sum release.txt"],
        more=[more({"op": "sha256sum", "sources": ["SHA256SUMS"], "check": True}, "sha256sum -c SHA256SUMS", ["sha256sum --check SHA256SUMS"],
                   ["sha256sum SHA256SUMS", "sha256sum -c --quiet SHA256SUMS"]),
              more({"op": "sha256sum", "sources": ["my release.txt"]}, "sha256sum 'my release.txt'", [], ["sha1sum 'my release.txt'"]),
              more({"op": "sha256sum", "sources": ["a.txt", "b.txt", "c.txt"]}, "sha256sum a.txt b.txt c.txt", [], ["sha256sum a.txt b.txt"]),
              more({"op": "sha256sum", "sources": ["zephyr-sums.sha256"], "check": True}, "sha256sum -c zephyr-sums.sha256", [], ["sha256sum zephyr-sums.sha256"])]),
    "sha512sum": dict(
        intent={"op": "sha512sum", "sources": ["ledger.txt"]},
        command="sha512sum ledger.txt",
        invalid=[{"op": "sha512sum", "sources": [""]}, {"op": "sha512sum"}],
        accept=["sha512sum -- ledger.txt"],
        reject=["sha256sum ledger.txt", "sha512sum < ledger.txt"],
        more=[more({"op": "sha512sum", "sources": ["SHA512SUMS"], "check": True}, "sha512sum -c SHA512SUMS", ["sha512sum --check SHA512SUMS"],
                   ["sha512sum SHA512SUMS", "sha512sum -c --quiet SHA512SUMS"]),
              more({"op": "sha512sum", "sources": ["data one.txt", "data two.txt"]}, "sha512sum 'data one.txt' 'data two.txt'",
                   [], ["sha512sum 'data two.txt' 'data one.txt'"]),
              more({"op": "sha512sum", "sources": ["-old-ledger.txt"]}, "sha512sum -- -old-ledger.txt", [], ["sha512sum < -old-ledger.txt"]),
              more({"op": "sha512sum", "sources": ["tundra-ledger.txt", "zephyr-ledger.txt"]},
                   "sha512sum tundra-ledger.txt zephyr-ledger.txt", [], ["sha512sum tundra-ledger.txt"])]),
    "cksum": dict(
        intent={"op": "cksum", "sources": ["invoice.txt"]},
        command="cksum invoice.txt",
        invalid=[{"op": "cksum", "sources": []}, {"op": "cksum"}, {"op": "cksum", "sources": ["a.txt"], "check": True}],
        accept=["cksum -- invoice.txt"],
        reject=["sum invoice.txt", "cksum < invoice.txt"],
        more=[more({"op": "cksum", "sources": ["invoice.txt", "receipt.txt"]}, "cksum invoice.txt receipt.txt",
                   ["cksum invoice.txt; cksum receipt.txt"], ["cksum receipt.txt invoice.txt"]),
              more({"op": "cksum", "sources": ["-my invoice.txt"]}, "cksum -- '-my invoice.txt'", [], ["cksum ./'-my invoice.txt'"]),
              more({"op": "cksum", "sources": ["empty.txt"]}, "cksum empty.txt", [], ["cksum < empty.txt", "sum empty.txt"]),
              more({"op": "cksum", "sources": ["tundra-notes.txt", "zephyr-empty.txt"]}, "cksum tundra-notes.txt zephyr-empty.txt",
                   [], ["cksum zephyr-empty.txt tundra-notes.txt"])]),
    "sum": dict(
        intent={"op": "sum", "sources": ["draft.txt"]},
        command="sum draft.txt",
        invalid=[{"op": "sum", "sources": []}, {"op": "sum"}],
        accept=["sum -r draft.txt"],
        reject=["sum -s draft.txt", "cksum draft.txt"],
        more=[more({"op": "sum", "sources": ["draft.txt", "final.txt"]}, "sum draft.txt final.txt"),
              more({"op": "sum", "sources": ["chapter one.txt", "chapter two.txt"]}, "sum 'chapter one.txt' 'chapter two.txt'",
                   [], ["sum 'chapter two.txt' 'chapter one.txt'"]),
              more({"op": "sum", "sources": ["notes.txt"], "sysv": True}, "sum -s notes.txt", ["sum --sysv notes.txt"], ["sum notes.txt"]),
              more({"op": "sum", "sources": ["-final draft.txt"]}, "sum -- '-final draft.txt'", [], ["sum -s -- '-final draft.txt'"]),
              more({"op": "sum", "sources": ["tundra-draft.txt"], "sysv": True}, "sum -s tundra-draft.txt", [], ["sum tundra-draft.txt"])]),
}


class TextCommandTests(BatchCase):
    def test_every_command_has_a_case(self):
        self.assertEqual(len(CASES), 25)

    def test_render_and_invalid_intents(self):
        for name, case in CASES.items():
            with self.subTest(name):
                self.assertEqual(render(case["intent"]), case["command"])
                for invalid in case["invalid"]:
                    with self.assertRaises(ValueError, msg=str(invalid)):
                        validate_intent(invalid)
                for extra in case["more"]:
                    self.assertEqual(render(extra["intent"]), extra["command"])

    def test_canonical_commands_equivalents_and_wrong_commands(self):
        for name, case in CASES.items():
            with self.subTest(name):
                self.assert_verdicts(case["intent"], [case["command"], *case["accept"]], case["reject"])

    def test_further_scenarios_and_their_wrong_commands(self):
        for name, case in CASES.items():
            for extra in case["more"]:
                with self.subTest(extra["command"]):
                    self.assert_verdicts(extra["intent"], [extra["command"], *extra["accept"]], extra["reject"])

    def test_catalog_scenarios_pass(self):
        for name in CASES:
            with self.subTest(name):
                self.assert_catalog_passes("text", name)


if __name__ == "__main__":
    unittest.main()
