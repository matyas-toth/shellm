"""Render Bash labels and check their intended effects independently."""

import base64
import fnmatch
import hashlib
import posixpath
import re
from types import SimpleNamespace

from shellbench.oracle import initial_state
from shellbench.sandbox import same_stdout
from .utilities import SPECS as UTILITY_SPECS
from .utilities.base import quote


def path(value):
    if value == "~":
        return "/home/shellm"
    return posixpath.normpath(value if value.startswith("/") else "/workspace/" + value)


def arguments(values):
    return ("-- " if any(v.startswith("-") for v in values) else "") + " ".join(quote(v) for v in values)


INTENT_FIELDS = {
    "pwd": (set(), set()),
    "cd": ({"destination"}, set()),
    "ls": ({"directory"}, {"long", "all", "one"}),
    "mkdir": ({"targets"}, {"parents", "mode"}),
    "touch": ({"targets"}, set()),
    "cp": ({"sources", "destination"}, {"into", "directory_source"}),
    "mv": ({"sources", "destination"}, {"into", "directory_source"}),
    "rm": ({"targets"}, {"recursive"}),
    "cat": ({"sources"}, set()),
    "head": ({"source", "count"}, {"bytes"}),
    "tail": ({"source", "count"}, {"bytes"}),
    "wc": ({"source", "unit"}, set()),
    "grep": ({"pattern", "source"}, {"ignore_case", "invert", "line_numbers", "count", "recursive"}),
    "find": ({"directory"}, {"maxdepth", "type", "pattern", "empty", "size_gt"}),
    "chmod": ({"targets"}, {"mode", "changes", "recursive", "directory_target"}),
}
if INTENT_FIELDS.keys() & UTILITY_SPECS.keys():
    raise ValueError(f"Operation defined twice: {sorted(INTENT_FIELDS.keys() & UTILITY_SPECS.keys())}")
INTENT_FIELDS.update({op: (set(spec.required), spec.optional) for op, spec in UTILITY_SPECS.items()})

PERM_BITS = {"r": 4, "w": 2, "x": 1}
CLASS_SHIFT = {"u": 6, "g": 3, "o": 0}


def classes(who):
    return "ugo" if who == "a" else who


def validate_changes(changes):
    if not isinstance(changes, list) or not changes:
        raise ValueError("Expected nonempty changes")
    for change in changes:
        if not isinstance(change, dict) or change.keys() != {"who", "op", "perms"}:
            raise ValueError(f"Invalid chmod change: {change}")
        if not all(isinstance(change[k], str) for k in change) or not re.fullmatch(r"a|u?g?o?", change["who"]) or not change["who"]:
            raise ValueError(f"Invalid chmod who: {change}")
        if change["op"] not in ("+", "-", "=") or not re.fullmatch(r"r?w?x?", change["perms"]):
            raise ValueError(f"Invalid chmod operation or permissions: {change}")
        if change["op"] != "=" and not change["perms"]:
            raise ValueError(f"Empty permissions need '=': {change}")


def apply_changes(mode, changes):
    for change in changes:
        value = sum(PERM_BITS[p] for p in change["perms"])
        for cls in classes(change["who"]):
            shift = CLASS_SHIFT[cls]
            if change["op"] == "+":
                mode |= value << shift
            elif change["op"] == "-":
                mode &= ~(value << shift)
            else:
                mode = (mode & ~(7 << shift)) | (value << shift)
    return mode


def validate_intent(intent):
    if not isinstance(intent, dict) or intent.get("op") not in INTENT_FIELDS:
        raise ValueError("Unknown intent operation")
    required, optional = INTENT_FIELDS[intent["op"]]
    if not required <= intent.keys() or intent.keys() - required - optional - {"op"}:
        raise ValueError(f"Missing or unknown intent fields: {intent}")
    if intent["op"] in UTILITY_SPECS:
        UTILITY_SPECS[intent["op"]].validate(intent)
        return
    text_fields = {"destination", "directory", "source", "pattern", "mode", "unit", "type"}
    for name, value in intent.items():
        if name in text_fields:
            if not isinstance(value, str) or not value or any(c in value for c in "\n\r\0"):
                raise ValueError(f"Invalid text argument {name}")
        elif name in ("sources", "targets"):
            if not isinstance(value, list) or not value or len(set(value)) != len(value):
                raise ValueError(f"Expected distinct nonempty {name}")
            if any(not isinstance(v, str) or not v or any(c in v for c in "\n\r\0") for v in value):
                raise ValueError(f"Invalid {name}")
        elif name in ("maxdepth", "size_gt") or (name == "count" and intent["op"] in ("head", "tail")):
            if type(value) is not int or value < 1:
                raise ValueError(f"Expected positive integer {name}")
        elif name == "changes":
            validate_changes(value)
        elif name != "op" and type(value) is not bool:
            raise ValueError(f"Expected boolean {name}")
    if "mode" in intent and not re.fullmatch(r"[0-7]{3}", intent["mode"]):
        raise ValueError("Expected three octal permission digits")
    if intent["op"] == "chmod":
        if ("mode" in intent) == ("changes" in intent):
            raise ValueError("chmod needs exactly one of mode or changes")
        if intent.get("directory_target") and intent.get("recursive"):
            raise ValueError("directory_target and recursive are exclusive")
        for change in intent.get("changes", []) if intent.get("recursive") else []:
            cleared = change["perms"] if change["op"] == "-" else "rwx".translate({ord(c): None for c in change["perms"]}) if change["op"] == "=" else ""
            if set(classes(change["who"])) & {"u"} and set(cleared) & {"r", "x"}:
                raise ValueError("Recursive changes must keep owner read and execute so chmod can descend")
    if intent.get("unit", "lines") not in ("lines", "words", "bytes") or intent.get("type", "f") not in ("f", "d"):
        raise ValueError("Unsupported unit or file type")
    if intent["op"] in ("cp", "mv") and len(intent["sources"]) > 1 and not intent.get("into"):
        raise ValueError("Multiple sources require a destination directory")
    if intent["op"] == "grep" and intent.get("recursive") and any(intent.get(k) for k in ("invert", "line_numbers", "count")):
        raise ValueError("Recursive grep supports matching file paths only")


def render(intent):
    validate_intent(intent)
    op = intent["op"]
    if op == "pwd":
        return "pwd"
    if op == "cd":
        return "cd ~" if intent["destination"] == "~" else "cd " + arguments([intent["destination"]])
    if op == "ls":
        flags = ("l" if intent.get("long") else "") + ("a" if intent.get("all") else "") + ("1" if intent.get("one") else "")
        return "ls" + (" -" + flags if flags else "") + (" " + arguments([intent["directory"]]) if intent["directory"] != "." else "")
    if op == "mkdir":
        options = (" -p" if intent.get("parents") else "") + (" -m " + intent["mode"] if intent.get("mode") else "")
        return "mkdir" + options + " " + arguments(intent["targets"])
    if op == "touch":
        return "touch " + arguments(intent["targets"])
    if op in ("cp", "mv"):
        options = " -r" if op == "cp" and intent.get("directory_source") else ""
        return op + options + " " + arguments(intent["sources"] + [intent["destination"]])
    if op == "rm":
        return "rm" + (" -r" if intent.get("recursive") else "") + " " + arguments(intent["targets"])
    if op == "chmod":
        spec = intent["mode"] if "mode" in intent else ",".join(c["who"] + c["op"] + c["perms"] for c in intent["changes"])
        return "chmod" + (" -R" if intent.get("recursive") else "") + " " + spec + " " + arguments(intent["targets"])
    if op == "cat":
        return "cat " + arguments(intent["sources"])
    if op in ("head", "tail"):
        return f"{op} -{'c' if intent.get('bytes') else 'n'} {intent['count']} " + arguments([intent["source"]])
    if op == "wc":
        return f"wc -{ {'lines': 'l', 'words': 'w', 'bytes': 'c'}[intent['unit']]} " + arguments([intent["source"]])
    if op == "grep":
        flags = "F" + "".join(letter for key, letter in (("ignore_case", "i"), ("invert", "v"), ("line_numbers", "n"), ("count", "c")) if intent.get(key))
        flags += "rl" if intent.get("recursive") else ""
        return f"grep -{flags} -- {quote(intent['pattern'])} {quote(intent['source'])}"
    if op == "find":
        command = "find " + quote(intent["directory"])
        if intent.get("maxdepth"):
            command += f" -maxdepth {intent['maxdepth']}"
        command += " -type " + intent.get("type", "f")
        if intent.get("pattern"):
            command += " -name " + quote(intent["pattern"])
        if intent.get("empty"):
            command += " -empty"
        if intent.get("size_gt"):
            command += f" -size +{intent['size_gt']}c"
        return command
    if op in UTILITY_SPECS:
        return UTILITY_SPECS[op].render(intent)
    raise ValueError(f"Unsupported intent operation: {op}")


def make_fixture(intent, seed):
    spec = {"directories": ["keep"], "files": {"keep/untouched.txt": "preserve this\n"}, "symlinks": {},
            "home_files": {"home-sentinel.txt": "preserve home\n"}}
    def directory(name):
        name = path(name)
        if name == "/workspace":
            return
        if not name.startswith("/workspace/"):
            if name not in ("/", "/home/shellm"):
                raise ValueError(f"Fixture path outside supported roots: {name}")
            return
        relative = name.removeprefix("/workspace/")
        parts = relative.split("/")
        for index in range(1, len(parts) + 1):
            item = "/".join(parts[:index])
            if item not in spec["directories"]:
                spec["directories"].append(item)
    def file(name, text=None):
        absolute = path(name)
        if not absolute.startswith("/workspace/"):
            raise ValueError(f"File outside fixture: {name}")
        directory(posixpath.dirname(absolute))
        spec["files"][absolute.removeprefix("/workspace/")] = text if text is not None else "".join(
            f"entry {i:02d} variant {seed} from {posixpath.basename(name)}\n" for i in range(1, 21 + seed))
    def binary(name, data):
        absolute = path(name)
        if not absolute.startswith("/workspace/"):
            raise ValueError(f"File outside fixture: {name}")
        directory(posixpath.dirname(absolute))
        spec.setdefault("binary_files", {})[absolute.removeprefix("/workspace/")] = base64.b64encode(data).decode()
    def symlink(name, target):
        absolute = path(name)
        if not absolute.startswith("/workspace/"):
            raise ValueError(f"Link outside fixture: {name}")
        directory(posixpath.dirname(absolute))
        spec["symlinks"][absolute.removeprefix("/workspace/")] = target
    op = intent["op"]
    if op == "cd":
        directory(intent["destination"])
    elif op == "ls":
        base = intent["directory"]
        directory(base)
        for name in ("first.txt", "second.log", ".private"):
            file(posixpath.join(base, name))
        directory(posixpath.join(base, "child"))
        file(posixpath.join(base, "child", "nested.txt"))
    elif op in ("mkdir", "touch"):
        for target in intent["targets"]:
            if op == "touch" or not intent.get("parents"):
                directory(posixpath.dirname(path(target)))
    elif op in ("cp", "mv"):
        for source in intent["sources"]:
            if intent.get("directory_source"):
                directory(source)
                file(posixpath.join(source, "item.txt"))
                file(posixpath.join(source, "inside", "nested.txt"))
            else:
                file(source)
        if intent.get("into"):
            directory(intent["destination"])
            file(posixpath.join(intent["destination"], "destination-sentinel.txt"))
        else:
            directory(posixpath.dirname(path(intent["destination"])))
    elif op == "rm":
        for target in intent["targets"]:
            if intent.get("recursive"):
                file(posixpath.join(target, "inside", "item.txt"))
            else:
                file(target)
    elif op == "chmod":
        for target in intent["targets"]:
            if intent.get("recursive") or intent.get("directory_target"):
                file(posixpath.join(target, "inside", "item.txt"))
            else:
                file(target)
    elif op == "cat":
        for source in intent["sources"]:
            file(source)
    elif op in ("head", "tail", "wc"):
        file(intent["source"])
    elif op == "grep":
        pattern = intent["pattern"]
        text = f"ordinary row {seed}\n{pattern} matching {seed}\nno match here\n{pattern.lower()} lowercase\n{pattern} another\n"
        # A regex interpretation of punctuation must not accidentally look correct.
        text += pattern.replace(".", "x").replace("+", "").replace("[", "").replace("]", "") + " decoy\n"
        if intent.get("recursive"):
            directory(intent["source"])
            file(posixpath.join(intent["source"], "first.txt"), text)
            file(posixpath.join(intent["source"], "nested", "second.txt"), f"{pattern} nested\n")
            file(posixpath.join(intent["source"], "plain.txt"), "unmatched\n")
        else:
            file(intent["source"], text)
    elif op == "find":
        base = intent["directory"]
        directory(base)
        extension = intent.get("pattern", "*.txt").rsplit(".", 1)[-1]
        file(posixpath.join(base, "first." + extension), "x" * (50 + seed))
        file(posixpath.join(base, "nested", "second." + extension), "y" * (300 + seed))
        file(posixpath.join(base, "empty." + extension), "")
        file(posixpath.join(base, "unrelated.bin"), "z\n")
        directory(posixpath.join(base, "directory." + extension))
    elif op in UTILITY_SPECS:
        UTILITY_SPECS[op].fixture(intent, seed, SimpleNamespace(file=file, directory=directory, binary=binary, symlink=symlink, seed=seed))
    return spec


def check_intent(intent, spec, outcome):
    expected_returncode = UTILITY_SPECS[intent["op"]].returncode if intent["op"] in UTILITY_SPECS else 0
    if not outcome["syntax_ok"] or outcome["returncode"] != expected_returncode or outcome["stderr"] or outcome["timed_out"] or outcome["output_overflow"]:
        raise ValueError(f"Reference execution failed: {outcome}")
    state = initial_state(spec)
    op = intent["op"]
    expected_cwd = path(intent["destination"]) if op == "cd" else "/workspace"
    def add_empty(name):
        state[path(name)] = {"mode": 0o644, "type": "file", "size": 0, "sha256": hashlib.sha256(b"").hexdigest()}
    if op == "mkdir":
        for target in intent["targets"]:
            current = path(target)
            state[current] = {"mode": int(intent.get("mode", "755"), 8), "type": "directory"}
            current = posixpath.dirname(current)
            while current.startswith("/workspace/") and current not in state:
                state[current] = {"mode": 0o755, "type": "directory"}
                current = posixpath.dirname(current)
    elif op == "touch":
        for target in intent["targets"]:
            add_empty(target)
    elif op in ("cp", "mv"):
        for source in intent["sources"]:
            src = path(source)
            dst = path(posixpath.join(intent["destination"], posixpath.basename(source))) if intent.get("into") else path(intent["destination"])
            subtree = {name: info for name, info in state.items() if name == src or name.startswith(src + "/")}
            for name, info in subtree.items():
                state[dst + name[len(src):]] = info.copy()
                if op == "mv":
                    del state[name]
    elif op == "rm":
        for target in intent["targets"]:
            state = {name: info for name, info in state.items() if name != path(target) and not name.startswith(path(target) + "/")}
    elif op == "chmod":
        for target in intent["targets"]:
            base = path(target)
            for name in state:
                if (name == base or (intent.get("recursive") and name.startswith(base + "/"))) and state[name]["type"] != "symlink":
                    mode = int(intent["mode"], 8) if "mode" in intent else apply_changes(state[name]["mode"], intent["changes"])
                    state[name] = {**state[name], "mode": mode}
    elif op in UTILITY_SPECS:
        files_text = {"/workspace/" + name: content for name, content in spec["files"].items()}
        binaries = {"/workspace/" + name: base64.b64decode(data) for name, data in spec.get("binary_files", {}).items()}
        context = SimpleNamespace(read=lambda name: files_text[path(name)], files=files_text, binaries=binaries,
                                  state=state, outcome=outcome, spec=spec)
        utility_result = UTILITY_SPECS[op].check(intent, context)
    if outcome["state"] != state or outcome["cwd"] != expected_cwd:
        raise ValueError(f"Wrong filesystem/cwd effect for {intent}")
    expected, mode = "", "exact"
    if op in UTILITY_SPECS:
        expected, mode = utility_result
    files = {"/workspace/" + name: content for name, content in spec["files"].items()}
    if op == "pwd":
        expected = "/workspace\n"
    elif op == "cat":
        expected = "".join(files[path(name)] for name in intent["sources"])
    elif op in ("head", "tail"):
        text, count = files[path(intent["source"])], intent["count"]
        if intent.get("bytes"):
            expected = (text.encode()[:count] if op == "head" else text.encode()[-count:]).decode()
        else:
            lines = text.splitlines(keepends=True)
            expected = "".join(lines[:count] if op == "head" else lines[-count:])
    elif op == "wc":
        text = files[path(intent["source"])]
        count = text.count("\n") if intent["unit"] == "lines" else len(text.split()) if intent["unit"] == "words" else len(text.encode())
        expected, mode = str(count) + "\n", "count"
    elif op == "grep":
        def matches(text):
            pattern = intent["pattern"].lower() if intent.get("ignore_case") else intent["pattern"]
            return pattern in (text.lower() if intent.get("ignore_case") else text)
        if intent.get("recursive"):
            base = path(intent["source"]) + "/"
            selected = [name for name, text in files.items() if name.startswith(base) and any(matches(line) for line in text.splitlines())]
            expected = "".join(name.removeprefix("/workspace/") + "\n" for name in selected)
            mode = "lines"
        else:
            lines = []
            for index, line in enumerate(files[path(intent["source"])].splitlines(keepends=True), 1):
                keep = not matches(line) if intent.get("invert") else matches(line)
                if keep:
                    lines.append((str(index) + ":" if intent.get("line_numbers") else "") + line)
            expected = str(len(lines)) + "\n" if intent.get("count") else "".join(lines)
    elif op == "find":
        base = path(intent["directory"])
        selected = []
        choices = state.copy()
        choices[base] = {"type": "directory"}
        for name, info in choices.items():
            if name != base and not name.startswith(base + "/"):
                continue
            relative = posixpath.relpath(name, base)
            depth = 0 if relative == "." else relative.count("/") + 1
            if intent.get("maxdepth") and depth > intent["maxdepth"]:
                continue
            if info["type"] != ("directory" if intent.get("type") == "d" else "file"):
                continue
            if intent.get("pattern") and not fnmatch.fnmatchcase(posixpath.basename(name), intent["pattern"]):
                continue
            if intent.get("empty") and info.get("size") != 0:
                continue
            if intent.get("size_gt") and info.get("size", 0) <= intent["size_gt"]:
                continue
            selected.append(intent["directory"] if relative == "." else posixpath.join(intent["directory"], relative))
        expected, mode = "".join(name + "\n" for name in selected), "lines"
    elif op == "ls":
        base = path(intent["directory"]) + "/"
        names = [name[len(base):] for name in state if name.startswith(base) and "/" not in name[len(base):]]
        names = [name for name in names if not name.startswith(".") or intent.get("all")]
        if intent.get("all"):
            names += [".", ".."]
        if intent.get("long"):
            listed = []
            for line in outcome["stdout"].splitlines():
                if line.startswith("total "):
                    continue
                parts = line.split(None, 8)
                if len(parts) != 9:
                    raise ValueError("Invalid long listing")
                listed.append(parts[-1])
            if sorted(names) != sorted(listed):
                raise ValueError("Wrong long listing entries")
            return
        expected, mode = "".join(name + "\n" for name in names), "lines"
    if not same_stdout(outcome["stdout"], expected, mode):
        raise ValueError(f"Wrong stdout for {intent}: {outcome['stdout']!r} != {expected!r}")
