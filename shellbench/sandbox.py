"""Docker lifecycle and comparison; generated commands never run on the host."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import uuid

from .oracle import check_reference

ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "eval" / "cases.jsonl"
IMAGE_TAG = "shellm-eval:pilot-v1"


def load_cases(path=SUITE):
    cases = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case IDs")
    for case in cases:
        if not all(case.get(key) for key in ("id", "family", "request", "reference", "comparison", "coverage")):
            raise ValueError(f"Incomplete case: {case}")
        if case["comparison"] not in ("exact", "lines", "count", "number", "listing"):
            raise ValueError(f"Unknown comparison mode: {case['id']}")
    return cases


def docker_cli():
    errors = []
    for name in ("docker", "docker.exe"):
        cli = shutil.which(name)
        if cli:
            check = subprocess.run([cli, "info", "--format", "{{.OSType}}"], capture_output=True, text=True, timeout=15)
            if check.returncode == 0 and check.stdout.strip() == "linux":
                return cli
            errors.append(check.stderr.strip() or check.stdout.strip())
    raise RuntimeError(f"A running Linux Docker engine is required: {errors}")


def build_image(cli):
    context = io.BytesIO()
    with tarfile.open(fileobj=context, mode="w") as archive:
        for source, target in ((ROOT / "eval" / "Dockerfile", "Dockerfile"),
                               (ROOT / "shellbench" / "worker.py", "worker.py")):
            data = source.read_bytes()
            member = tarfile.TarInfo(target)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    result = subprocess.run([cli, "build", "--tag", IMAGE_TAG, "-"], input=context.getvalue(),
                            capture_output=True, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return image_id(cli)


def image_id(cli):
    result = subprocess.run([cli, "image", "inspect", "--format", "{{.Id}}", IMAGE_TAG],
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError("Evaluation image missing; run python -m shellbench build")
    return result.stdout.strip()


def run_container(cli, image, items, fixtures):
    name = f"shellm-eval-{uuid.uuid4().hex}"
    args = [cli, "run", "--rm", "--init", "--name", name, "--interactive",
            "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges=true", "--user", "1000:1000",
            "--pids-limit", "64", "--memory", "128m", "--memory-swap", "128m", "--cpus", "1",
            "--tmpfs", "/workspace:rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000,mode=0755",
            "--tmpfs", "/home/shellm:rw,nosuid,nodev,noexec,size=4m,uid=1000,gid=1000,mode=0755",
            "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=8m,mode=1777", image]
    try:
        result = subprocess.run(args, input=json.dumps({"items": items, "fixtures": fixtures}).encode(),
                                capture_output=True, timeout=20 + len(items) * len(fixtures) * 6)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        subprocess.run([cli, "rm", "--force", name], capture_output=True, timeout=15)
        raise
    if result.returncode:
        raise RuntimeError(f"Container failed (not a model score): {result.stderr.decode(errors='replace')}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Worker returned invalid results") from error
    if set(data) != {item["id"] for item in items}:
        raise RuntimeError("Worker result IDs do not match submitted cases")
    return data


def reference_results(cli, image, cases, fixtures):
    key = hashlib.sha256(json.dumps([image, cases, fixtures], sort_keys=True).encode()).hexdigest()
    cache = ROOT / ".cache" / "shellbench" / f"references-{key}.json"
    results = json.loads(cache.read_text()) if cache.exists() else run_container(
        cli, image, [{"id": c["id"], "command": c["reference"]} for c in cases], fixtures)
    for case in cases:
        for spec, outcome in zip(fixtures, results[case["id"]], strict=True):
            if not outcome["syntax_ok"] or outcome["returncode"] != 0 or outcome["timed_out"] or outcome["output_overflow"]:
                raise RuntimeError(f"Invalid reference for {case['id']}: {outcome}")
            check_reference(case, spec, outcome)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(results), encoding="utf-8")
    return results


def same_stdout(actual, expected, mode):
    if mode == "listing":
        def fields(text):
            rows = []
            for line in text.splitlines():
                if re.fullmatch(r"total \d+", line):
                    continue
                parts = line.split(None, 8)
                if len(parts) != 9 or not re.fullmatch(r"[bcdlps-][rwxStTs-]{9}[+.]?", parts[0]):
                    return None
                if not parts[1].isdigit() or not parts[4].isdigit():
                    return None
                rows.append(tuple(parts[:5] + [parts[8]]))
            return sorted(rows)
        a, b = fields(actual), fields(expected)
        return a is not None and b is not None and a == b
    if mode == "lines":
        return sorted(actual.splitlines()) == sorted(expected.splitlines())
    if mode in ("count", "number"):
        # A count alone and GNU wc's count followed by a filename are both acceptable.
        pattern = r"\s*(\d+)" + (r"(?:[ \t]+[^\n]+)?" if mode == "count" else "") + r"[ \t]*\n?"
        a, b = re.fullmatch(pattern, actual), re.fullmatch(pattern, expected)
        return bool(a and b and int(a.group(1)) == int(b.group(1)))
    return actual == expected


def compare(actual, expected, mode):
    reasons = []
    if not actual["syntax_ok"]:
        reasons.append("invalid_syntax")
    if actual["timed_out"]:
        reasons.append("timeout")
    if actual["output_overflow"]:
        reasons.append("output_limit")
    if actual["returncode"] != expected["returncode"]:
        reasons.append("exit_status")
    if actual["cwd"] != expected["cwd"]:
        reasons.append("working_directory")
    if not same_stdout(actual["stdout"], expected["stdout"], mode):
        reasons.append("stdout")
    if actual["stderr"] != expected["stderr"]:
        reasons.append("stderr")
    if actual["state"] != expected["state"]:
        reasons.append("filesystem")
    return reasons


def extract_command(raw):
    command = raw.split("\n", 1)[0].strip()
    markdown = "```" in command or (command.startswith("`") and command.endswith("`"))
    return command, bool(command) and raw.strip() == command and not markdown


def evaluate(cli, image, cases, fixtures, predictions, workers=4):
    references = reference_results(cli, image, cases, fixtures)
    def one(case):
        prediction = predictions[case["id"]]
        raw = prediction["completion"]
        command, format_ok = extract_command(raw)
        if not command:
            return {"id": case["id"], "family": case["family"], "command": "", "raw_completion": raw,
                    "format_ok": False, "exact_match": False, "functional_ok": False,
                    "syntax_ok": False, "fixtures": [{"passed": False, "reasons": ["empty_output"]}]}
        outputs = run_container(cli, image, [{"id": case["id"], "command": command}], fixtures)[case["id"]]
        checks = []
        for seed, (actual, expected) in enumerate(zip(outputs, references[case["id"]], strict=True)):
            reasons = compare(actual, expected, case["comparison"])
            checks.append({"seed": seed, "passed": not reasons, "reasons": reasons,
                           "returncode": actual["returncode"], "stdout": actual["stdout"],
                           "stderr": actual["stderr"], "cwd": actual["cwd"]})
        return {"id": case["id"], "family": case["family"], "command": command, "raw_completion": raw,
                "format_ok": format_ok, "exact_match": command == case["reference"],
                "functional_ok": all(c["passed"] for c in checks),
                "syntax_ok": all(o["syntax_ok"] for o in outputs), "fixtures": checks}
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(one, cases):
            rows.append(row)
            if len(rows) % 14 == 0 or len(rows) == len(cases):
                print(f"Evaluated {len(rows)}/{len(cases)}", flush=True)
    return rows
