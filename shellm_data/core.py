"""Compile checked source catalogs into portable, fully rendered JSONL releases."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

from shellbench.sandbox import ROOT, SUITE, docker_cli, image_id, run_container
from .intents import check_intent, make_fixture, render

DATA = ROOT / "data" / "shell_translation"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def normalize_request(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def source_groups(release):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", release):
        raise ValueError("Release IDs must contain lowercase letters, digits, hyphens, or underscores")
    result = []
    for source in sorted((DATA / "catalogs" / release).rglob("*.json")):
        groups = json.loads(source.read_text(encoding="utf-8"))
        for group in groups:
            if group.keys() != {"id", "family", "topic", "capability", "split", "intent", "requests"}:
                raise ValueError(f"Unexpected catalog fields in {source}")
            for field in ("id", "family", "topic", "capability"):
                if not isinstance(group[field], str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", group[field]):
                    raise ValueError(f"Invalid catalog {field}: {source}")
            if group["family"] != group["intent"]["op"]:
                raise ValueError(f"Family differs from intent operation: {source}")
            if not isinstance(group["requests"], list) or not group["requests"] or any(not isinstance(r, str) for r in group["requests"]):
                raise ValueError(f"Requests must be a nonempty string list: {source}")
            group = dict(group, source=str(source.relative_to(ROOT)).replace("\\", "/"))
            result.append(group)
    if not result:
        raise ValueError(f"No source groups for {release}")
    return sorted(result, key=lambda group: (group["source"], group["id"]))


def compile_examples(groups, release):
    records = []
    for group in groups:
        command = render(group["intent"])
        for index, request in enumerate(group["requests"], 1):
            records.append({"schema_version": 1, "id": f"{group['id']}-p{index:02d}", "group_id": group["id"],
                            "family": group["family"], "topic": group["topic"], "capability": group["capability"],
                            "split": group["split"], "request": request, "command": command,
                            "intent": group["intent"], "provenance": {"release": release, "source": group["source"],
                            "method": "command-first intent catalog with authored paraphrases"}})
    return records


def check_records(records):
    reserved_suites = [SUITE, *sorted((ROOT / "eval").glob("*/cases.jsonl"))]
    eval_requests = {normalize_request(json.loads(line)["request"]) for suite in reserved_suites
                     for line in suite.read_text(encoding="utf-8").splitlines() if line.strip()}
    extra_commands = {json.loads(line)["reference"] for suite in reserved_suites if suite != SUITE
                      for line in suite.read_text(encoding="utf-8").splitlines() if line.strip()}
    seen, requests, groups = set(), set(), {}
    for row in records:
        if row["id"] in seen:
            raise ValueError(f"Duplicate ID: {row['id']}")
        seen.add(row["id"])
        request = normalize_request(row["request"])
        if request in requests or request in eval_requests:
            raise ValueError(f"Duplicate or evaluation-overlapping request: {row['request']}")
        requests.add(request)
        if row["command"] in extra_commands:
            raise ValueError(f"Command label reserved by separate evaluation: {row['id']}")
        if not row["request"].strip() or not row["command"].strip() or any(c in row["request"] + row["command"] for c in "\n\r\0"):
            raise ValueError("Requests and commands must be nonempty single lines")
        if row["split"] not in ("train", "validation") or row["schema_version"] != 1:
            raise ValueError("Invalid split or schema version")
        if row["command"] != render(row["intent"]):
            raise ValueError(f"Label does not match declared intent: {row['id']}")
        previous = groups.setdefault(row["group_id"], (row["split"], row["command"], row["intent"]))
        if previous != (row["split"], row["command"], row["intent"]):
            raise ValueError(f"Group spans splits or intents: {row['group_id']}")
    return {"examples": len(records), "groups": len(groups), "unique_commands": len({r["command"] for r in records}),
            "splits": dict(Counter(r["split"] for r in records)), "families": dict(Counter(r["family"] for r in records)),
            "evaluation_request_overlap": 0, "dataset_sha256": digest(records)}


def build(release, check=False):
    records = compile_examples(source_groups(release), release)
    summary = check_records(records)
    directory = DATA / "releases" / release
    files = {}
    for row in records:
        key = f"families/{row['topic']}/{row['family']}.jsonl"
        files.setdefault(key, []).append(row)
    manifest = {"schema_version": 1, "release": release, **summary,
                "files": [{"path": name, "examples": len(rows), "sha256": hashlib.sha256(
                    "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode()).hexdigest()}
                    for name, rows in sorted(files.items())]}
    if check:
        if json.loads((directory / "manifest.json").read_text()) != manifest:
            raise ValueError("Manifest differs from source catalogs; create a new release")
    elif directory.exists():
        raise ValueError("Release already exists; use --check or create a new release ID")
    for name, rows in files.items():
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        target = directory / name
        if check:
            if target.read_text(encoding="utf-8") != text:
                raise ValueError(f"Compiled data mismatch: {name}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    if not check:
        (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_release(release="pilot-v1"):
    directory = DATA / "releases" / release
    manifest = json.loads((directory / "manifest.json").read_text())
    records = []
    for item in manifest["files"]:
        source = directory / item["path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Changed data shard: {source}")
        records += [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    # Normalize the same source order used by the release compiler.
    records.sort(key=lambda row: (row["provenance"]["source"], row["group_id"], row["id"]))
    if check_records(records)["dataset_sha256"] != manifest["dataset_sha256"]:
        raise ValueError("Dataset content fingerprint mismatch")
    return records, manifest


def validate(release):
    records, manifest = load_release(release)
    groups = {}
    for row in records:
        groups.setdefault(row["group_id"], row)
    cli, image = docker_cli(), None
    image = image_id(cli)
    group_list = list(groups.values())
    def batch(rows):
        items = [{"id": row["group_id"], "command": row["command"],
                  "fixtures": [make_fixture(row["intent"], seed) for seed in (0, 1)]} for row in rows]
        outcomes = run_container(cli, image, items, [make_fixture({"op": "pwd"}, 0)] * 2)
        for item, row in zip(items, rows, strict=True):
            for spec, outcome in zip(item["fixtures"], outcomes[item["id"]], strict=True):
                try:
                    check_intent(row["intent"], spec, outcome)
                except ValueError as error:
                    raise ValueError(f"Invalid training label {row['group_id']}: {error}") from error
        return len(rows)
    done = 0
    batches = [group_list[index:index + 20] for index in range(0, len(group_list), 20)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for count in pool.map(batch, batches):
            done += count
            print(f"Validated {done}/{len(groups)} intent groups", flush=True)
    report = {"release": release, "dataset_sha256": manifest["dataset_sha256"], "image_id": image,
              "examples": len(records), "validated_groups": len(groups), "fixtures_per_group": 2,
              "command_executions": len(groups) * 2, "all_passed": True, "evaluation_request_overlap": 0,
              "validator_sha256": hashlib.sha256((Path(__file__).with_name("intents.py")).read_bytes()).hexdigest()}
    (DATA / "releases" / release / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
