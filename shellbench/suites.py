"""Versioned benchmark selection; the training release remains separate."""

import hashlib
from pathlib import Path

from .fixtures import fixture
from .sandbox import ROOT, SUITE

SUITES = {
    "shellbench-v1": SUITE,
    "shellbench-extra-v1": ROOT / "eval" / "shellbench-extra-v1" / "cases.jsonl",
}


def suite_path(name):
    return SUITES[name]


def suite_fixtures(name):
    if name == "shellbench-extra-v1":
        from .extra_fixtures import fixture as extra_fixture
        return [extra_fixture(0), extra_fixture(1)]
    return [fixture(0), fixture(1)]


def evaluator_digest(name):
    files = ["__main__.py", "sandbox.py", "oracle.py", "fixtures.py", "worker.py", "suites.py"]
    if name == "shellbench-extra-v1":
        files += ["extra_fixtures.py", "extra_oracle.py"]
    return hashlib.sha256(b"".join((Path(__file__).parent / file).read_bytes() for file in files)).hexdigest()
