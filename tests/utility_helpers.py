"""Docker-backed helpers shared by the table-driven command family tests."""

import json
import unittest

from shellbench.sandbox import ROOT, docker_cli, image_id, run_container
from shellm_data.intents import check_intent, make_fixture, render

CATALOGS = ROOT / "data" / "shell_translation" / "catalogs" / "pilot-v1"


class UtilityCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = docker_cli()
        cls.image = image_id(cls.cli)

    def accepts(self, intent, command):
        """Run `command` on both fixtures; True only if the independent oracle accepts it on both."""
        fixtures = [make_fixture(intent, seed) for seed in (0, 1)]
        outcomes = run_container(self.cli, self.image, [{"id": "t", "command": command, "fixtures": fixtures}],
                                 [make_fixture({"op": "pwd"}, 0)] * 2)["t"]
        try:
            for spec, outcome in zip(fixtures, outcomes, strict=True):
                check_intent(intent, spec, outcome)
        except ValueError:
            return False
        return True

    def assert_catalog_passes(self, topic, command):
        groups = json.loads((CATALOGS / topic / f"{command}.json").read_text(encoding="utf-8"))
        self.assertTrue(groups, command)
        for group in groups:
            self.assertEqual(group["family"], command)
            self.assertTrue(self.accepts(group["intent"], render(group["intent"])), group["id"])
