"""Extra v1 separation audit and provenance for verified references."""

from collections import Counter
from datetime import datetime
import hashlib
import json
from zoneinfo import ZoneInfo

from .sandbox import ROOT, SUITE
from .suites import evaluator_digest, suite_path


def normalized(text):
    import re
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def audit(cases):
    path = suite_path("shellbench-extra-v1")
    manifest = json.loads((path.parent / "manifest.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["cases_sha256"]:
        raise ValueError("Frozen Extra v1 cases differ from the manifest; create a new benchmark version")
    requests = [normalized(c["request"]) for c in cases]
    if len(cases) != 300 or len(set(requests)) != 300:
        raise ValueError("Extra requires 300 distinct requests")
    if len({case["reference"] for case in cases}) != 300:
        raise ValueError("Extra references must describe distinct concrete command scenarios")
    paths = list((ROOT / "data" / "shell_translation").rglob("*.jsonl"))
    other = [json.loads(line) for source in paths + [SUITE] for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    overlaps = set(requests) & {normalized(row["request"]) for row in other}
    references = {case["reference"] for case in cases}
    commands = {row.get("command", row.get("reference")) for row in other}
    if overlaps or references & commands:
        raise ValueError("Extra overlaps existing request or exact command labels")
    training_sources = list((ROOT / "data" / "shell_translation" / "catalogs").rglob("*.json"))
    source_requests = {normalized(request) for source in training_sources
                       for group in json.loads(source.read_text(encoding="utf-8")) for request in group["requests"]}
    if set(requests) & source_requests:
        raise ValueError("Extra overlaps editable training catalogs")
    for case in cases:
        if "split" in case or "intent" in case or not isinstance(case.get("expectation"), dict):
            raise ValueError("Extra cases are standalone evaluation records")
        if "\n" in case["request"] or "\n" in case["reference"]:
            raise ValueError("Requests and references must remain single lines")
    return {"cases": len(cases), "families": dict(Counter(case["family"] for case in cases)),
            "difficulty": dict(Counter(case["difficulty"] for case in cases)),
            "training_and_validation_request_overlap": 0, "original_shellbench_request_overlap": 0,
            "exact_existing_command_overlap": 0,
            "training_files_sha256": {source.relative_to(ROOT).as_posix(): hashlib.sha256(source.read_bytes()).hexdigest()
                                      for source in sorted(paths)},
            "suite_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def validation_report(cases, fixtures, image):
    return {"suite": "shellbench-extra-v1", "date": datetime.now(ZoneInfo("Europe/Budapest")).isoformat(),
            **audit(cases), "fixtures": len(fixtures), "reference_executions": len(cases) * len(fixtures),
            "fixtures_sha256": hashlib.sha256(json.dumps(fixtures, sort_keys=True).encode()).hexdigest(),
            "evaluator_sha256": evaluator_digest("shellbench-extra-v1"), "image_id": image, "all_passed": True}
