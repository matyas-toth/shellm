"""Container-only worker. Never invoke this against a host filesystem."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

WORK = Path("/workspace")
HOME = Path("/home/shellm")
LIMIT = 65536
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(HOME),
       "LC_ALL": "C", "LANG": "C", "TZ": "UTC", "TERM": "dumb"}


def reset(spec):
    for root in (WORK, HOME):
        for child in root.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    for directory in spec["directories"]:
        (WORK / directory).mkdir(parents=True, exist_ok=True)
    for root, key in ((WORK, "files"), (HOME, "home_files")):
        for name, content in spec[key].items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    for name, target in spec["symlinks"].items():
        (WORK / name).symlink_to(target)
    for root in (WORK, HOME):
        for path in sorted(root.rglob("*"), reverse=True):
            if not path.is_symlink():
                path.chmod(0o755 if path.is_dir() else 0o644)
                os.utime(path, (1700000000, 1700000000))
        os.utime(root, (1700000000, 1700000000))


def snapshot():
    result = {}
    for root in (WORK, HOME):
        for current, directories, files in os.walk(root, followlinks=False):
            for name in directories + files:
                path = Path(current) / name
                info = path.lstat()
                record = {"mode": stat.S_IMODE(info.st_mode)}
                if stat.S_ISLNK(info.st_mode):
                    record.update(type="symlink", target=os.readlink(path))
                elif stat.S_ISDIR(info.st_mode):
                    record.update(type="directory")
                elif stat.S_ISREG(info.st_mode):
                    with path.open("rb") as stream:
                        digest = hashlib.file_digest(stream, "sha256").hexdigest()
                    record.update(type="file", size=info.st_size, sha256=digest)
                else:
                    record.update(type="special")
                result[str(path)] = record
    return result


def execute(command, spec):
    reset(spec)
    syntax = subprocess.run(["bash", "--noprofile", "--norc", "-n", "-c", command],
                            env=ENV, capture_output=True, timeout=2)
    if syntax.returncode:
        return {"syntax_ok": False, "returncode": syntax.returncode,
                "stderr": syntax.stderr.decode(errors="replace"), "stdout": "",
                "cwd": None, "state": snapshot(), "timed_out": False, "output_overflow": False}
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr, tempfile.TemporaryFile() as cwd:
        descriptor = cwd.fileno()
        wrapper = f'eval "$1"; status=$?; printf "%s" "$PWD" >&{descriptor}; exit "$status"'
        process = subprocess.Popen(
            ["bash", "--noprofile", "--norc", "-c", wrapper, "shellbench", command],
            cwd=WORK, env=ENV, stdout=stdout, stderr=stderr,
            pass_fds=(descriptor,), start_new_session=True,
        )
        timed_out = False
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Kill remaining descendants even when the original shell has exited.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        stdout.seek(0)
        stderr.seek(0)
        cwd.seek(0)
        out, err = stdout.read(LIMIT + 1), stderr.read(LIMIT + 1)
        return {
            "syntax_ok": True, "returncode": process.returncode,
            "stdout": out[:LIMIT].decode(errors="replace"), "stderr": err[:LIMIT].decode(errors="replace"),
            "cwd": cwd.read(4096).decode(errors="replace"), "state": snapshot(),
            "timed_out": timed_out, "output_overflow": len(out) > LIMIT or len(err) > LIMIT,
        }


def main():
    if not Path("/.dockerenv").exists() or os.getuid() == 0:
        raise SystemExit("This worker must run inside its non-root evaluation container")
    os.umask(0o022)
    payload = json.load(sys.stdin)
    results = {}
    for item in payload["items"]:
        results[item["id"]] = [execute(item["command"], spec) for spec in payload["fixtures"]]
    json.dump(results, sys.stdout)


if __name__ == "__main__":
    main()
