"""Independent intent checks for the curated references, without executing shell."""

import fnmatch
import hashlib
from pathlib import PurePosixPath
import re


def initial_state(spec):
    state = {}
    for relative in spec["directories"]:
        path = PurePosixPath("/workspace") / relative
        while str(path) != "/workspace":
            state[str(path)] = {"mode": 0o755, "type": "directory"}
            path = path.parent
    for base, key in (("/workspace", "files"), ("/home/shellm", "home_files")):
        for relative, text in spec[key].items():
            content = text.encode()
            state[f"{base}/{relative}"] = {"mode": 0o644, "type": "file", "size": len(content),
                                           "sha256": hashlib.sha256(content).hexdigest()}
    for relative, target in spec["symlinks"].items():
        state[f"/workspace/{relative}"] = {"mode": 0o777, "type": "symlink", "target": target}
    return state


def intended_state(case_id, spec):
    state = initial_state(spec)
    mkdir = {
        "mkdir-01": ["projects"], "mkdir-02": ["backups"], "mkdir-03": ["project drafts"],
        "mkdir-04": ["build", "build/cache"], "mkdir-05": ["alpha", "beta"],
        "mkdir-06": ["docs/reports"], "mkdir-07": ["private"], "mkdir-08": ["-drafts"],
    }
    touch = {"touch-01": ["new.txt"], "touch-02": ["meeting notes.txt"], "touch-03": ["docs/new.md"],
             "touch-04": ["a.txt", "b.txt"], "touch-05": ["-new.txt"], "touch-06": ["client's notes.txt"],
             "touch-07": ["archive/placeholder.txt"], "touch-08": ["scratch.txt"]}
    copies = {
        "cp-01": [("notes.txt", "copy.txt")], "cp-02": [("notes.txt", "notes backup.txt")],
        "cp-03": [("docs", "docs-copy")], "cp-04": [("src/main.py", "archive/main.py")],
        "cp-05": [("docs/intro.md", "archive/intro.md")],
        "cp-06": [("notes.txt", "archive/notes.txt"), ("report.txt", "archive/report.txt")],
        "cp-07": [("-draft.txt", "draft-copy.txt")], "cp-08": [("client's plan.txt", "plan-copy.txt")],
    }
    moves = {
        "mv-01": [("notes.txt", "renamed.txt")], "mv-02": [("notes.txt", "meeting notes.txt")],
        "mv-03": [("report.txt", "archive/report.txt")], "mv-04": [("docs", "documents")],
        "mv-05": [("notes.txt", "archive/notes.txt"), ("report.txt", "archive/report.txt")],
        "mv-06": [("-draft.txt", "draft.txt")], "mv-07": [("client's plan.txt", "archive/plan.txt")],
        "mv-08": [("src/main.py", "main.py")],
    }
    removals = {"rm-01": ["old.log"], "rm-02": ["old.log", "app.log"], "rm-03": ["todo list.txt"],
                "rm-04": ["docs/old.log"], "rm-05": ["obsolete"], "rm-06": ["-draft.txt"],
                "rm-07": ["client's plan.txt"], "rm-08": ["src/helper.py"]}
    for name in mkdir.get(case_id, []):
        state[f"/workspace/{name}"] = {"mode": 0o700 if case_id == "mkdir-07" else 0o755, "type": "directory"}
    for name in touch.get(case_id, []):
        state[f"/workspace/{name}"] = {"mode": 0o644, "type": "file", "size": 0,
                                       "sha256": hashlib.sha256(b"").hexdigest()}
    for pairs, remove_source in ((copies.get(case_id, []), False), (moves.get(case_id, []), True)):
        for source, target in pairs:
            src, dst = f"/workspace/{source}", f"/workspace/{target}"
            subtree = {name: data for name, data in state.items() if name == src or name.startswith(src + "/")}
            for name, data in subtree.items():
                state[dst + name[len(src):]] = data.copy()
                if remove_source:
                    del state[name]
    for relative in removals.get(case_id, []):
        path = f"/workspace/{relative}"
        state = {name: data for name, data in state.items() if name != path and not name.startswith(path + "/")}
    return state


def check_reference(case, spec, outcome):
    ident, family = case["id"], case["family"]
    number = int(ident.split("-")[1])
    files = spec["files"]
    if outcome["state"] != intended_state(ident, spec):
        raise ValueError(f"Reference violates intended filesystem effect: {ident}")
    directories = ["/", "/home/shellm", "/", "/workspace/docs", "/workspace/src",
                   "/workspace/my projects", "/workspace/client's files", "/workspace/archive"]
    cwd = directories[number - 1] if family == "cd" else "/workspace"
    if outcome["cwd"] != cwd or outcome["stderr"]:
        raise ValueError(f"Unexpected reference cwd/stderr: {ident}")
    expected = ""
    actual = outcome["stdout"]
    if family == "pwd":
        expected = "/workspace\n"
    elif family == "cat":
        groups = [["notes.txt"], ["README.md"], ["todo list.txt"], ["notes.txt", "report.txt"],
                  ["-draft.txt"], ["client's plan.txt"], ["docs/intro.md"], ["unicode.txt"]]
        expected = "".join(files[name] for name in groups[number - 1])
    elif family in ("head", "tail"):
        names = ["README.md", "notes.txt", "numbers.txt", "report.txt", "todo list.txt", "notes.txt", "README.md", "numbers.txt"]
        counts = [5, 2, 10, 1, 1, 4, 7, 3]
        content, count = files[names[number - 1]], counts[number - 1]
        if number == 6:
            expected = (content.encode()[:count] if family == "head" else content.encode()[-count:]).decode()
        else:
            lines = content.splitlines(keepends=True)
            expected = "".join(lines[:count] if family == "head" else lines[-count:])
    elif family == "wc":
        names = ["report.txt", "notes.txt", "unicode.txt", "todo list.txt", "README.md", "docs/intro.md", "notes.txt", "numbers.txt"]
        content = files[names[number - 1]]
        count = len(content.split()) if number in (2, 6) else len(content.encode()) if number in (3, 7) else content.count("\n")
        if int(actual.split()[0]) != count:
            raise ValueError(f"Wrong reference count: {ident}")
        return
    elif family == "grep":
        if number == 7:
            expected_paths = ["./" + name for name, content in files.items() if "TODO" in content]
            if sorted(actual.splitlines()) != sorted(expected_paths):
                raise ValueError(f"Wrong recursive grep reference: {ident}")
            return
        name = "todo list.txt" if number == 8 else "notes.txt"
        matches = []
        for index, line in enumerate(files[name].splitlines(keepends=True), 1):
            match = "todo" in line.lower() if number == 2 else "a.b" in line if number == 6 else "TODO" in line
            if number == 4:
                match = not match
            if match:
                matches.append(f"{index}:{line}" if number == 3 else line)
        expected = str(len(matches)) + "\n" if number == 5 else "".join(matches)
    elif family == "find":
        if number == 5:
            paths = ["."] + [name.removeprefix("/workspace/") for name, data in initial_state(spec).items()
                              if name.startswith("/workspace/") and data["type"] == "directory"]
            expected_paths = ["." if name == "." else "./" + name for name in paths]
        else:
            tests = {
                1: lambda name, text: fnmatch.fnmatchcase(name, "*.log"),
                2: lambda name, text: name.startswith("docs/"),
                3: lambda name, text: fnmatch.fnmatchcase(name, "*.py"),
                4: lambda name, text: "/" not in name,
                6: lambda name, text: name.split("/")[-1] == "todo list.txt",
                7: lambda name, text: not text,
                8: lambda name, text: fnmatch.fnmatchcase(name, "*.log") and len(text.encode()) > 100,
            }
            expected_paths = [(name if number == 2 else "./" + name) for name, text in files.items() if tests[number](name, text)]
        if sorted(actual.splitlines()) != sorted(expected_paths):
            raise ValueError(f"Wrong find reference results: {ident}")
        return
    elif family == "ls":
        directory = "docs" if number in (5, 8) else "my projects" if number == 6 else "src" if number == 7 else ""
        prefix = "/workspace/" + (directory + "/" if directory else "")
        names = [name[len(prefix):] for name in initial_state(spec) if name.startswith(prefix) and "/" not in name[len(prefix):]]
        names = [name for name in names if not name.startswith(".") or number in (2, 4, 8)]
        if number in (2, 4, 8):
            names += [".", ".."]
        if number in (3, 4):
            listed = []
            for line in actual.splitlines()[1:]:
                match = re.match(r"^[dl-][rwx-]{9}\s+\d+\s+\S+\s+\S+\s+\d+\s+\w+\s+\d+\s+[\d:]+\s+(.*)$", line)
                if not match:
                    raise ValueError(f"Unrecognized long listing: {ident}: {line}")
                listed.append(match.group(1).split(" -> ", 1)[0])
            if sorted(listed) != sorted(names):
                raise ValueError(f"Wrong long listing contents: {ident}")
            return
        if sorted(actual.splitlines()) != sorted(names):
            raise ValueError(f"Wrong listing reference: {ident}")
        return
    if actual != expected:
        raise ValueError(f"Wrong reference output: {ident}: {actual!r} != {expected!r}")
