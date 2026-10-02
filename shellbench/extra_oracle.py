"""Independent Python expectations for Extra v1, never derived by parsing commands."""

from collections import Counter
import fnmatch
import hashlib
import posixpath
import re
import stat

from .oracle import initial_state


def absolute(name):
    return posixpath.normpath(name if name.startswith("/") else "/workspace/" + name)


def selected(query, spec):
    state = initial_state(spec)
    root = absolute(query["root"])
    choices = dict(state)
    choices.setdefault(root, {"type": "directory", "mode": 0o755})
    result = []
    for name, info in choices.items():
        if name != root and not name.startswith(root + "/"):
            continue
        relative = posixpath.relpath(name, root)
        depth = 0 if relative == "." else relative.count("/") + 1
        if query.get("type") and info["type"] != {"f": "file", "d": "directory", "l": "symlink"}[query["type"]]:
            continue
        if depth < query.get("min_depth", 0) or depth > query.get("max_depth", 100):
            continue
        if any(name == absolute(excluded) or name.startswith(absolute(excluded) + "/") for excluded in query.get("exclude", [])):
            continue
        basename = posixpath.basename(name)
        if query.get("pattern"):
            pattern = query["pattern"]
            if query.get("ignore_case"):
                basename, pattern = basename.lower(), pattern.lower()
            if not fnmatch.fnmatchcase(basename, pattern):
                continue
        if query.get("patterns") and not any(fnmatch.fnmatchcase(basename, p) for p in query["patterns"]):
            continue
        if "size_gt" in query and info.get("size", 0) <= query["size_gt"]:
            continue
        if "size_lt" in query and info.get("size", 0) >= query["size_lt"]:
            continue
        if query.get("empty"):
            empty = info.get("size") == 0 if info["type"] == "file" else not any(p.startswith(name + "/") for p in state)
            if not empty:
                continue
        if "contains" in query:
            text = spec["files"].get(name.removeprefix("/workspace/"), "")
            if query["contains"] not in text:
                continue
        result.append(name)
    return sorted(result)


def expression(expr, spec):
    if isinstance(expr, str):
        return expr
    op = expr["op"]
    if op == "exists_text":
        return expr["yes"] if absolute(expr["path"]) in initial_state(spec) else expr["no"]
    if op == "file":
        path = absolute(expr["path"])
        return spec["home_files"][path.removeprefix("/home/shellm/")] if path.startswith("/home/shellm/") else spec["files"][path.removeprefix("/workspace/")]
    if op == "concat":
        return "".join(expression(part, spec) for part in expr["parts"])
    if op == "paths":
        paths = selected(expr, spec)
        root = absolute(expr["root"])
        lines = []
        state = initial_state(spec)
        for name in paths:
            relative = posixpath.relpath(name, root)
            displayed = expr["root"] if relative == "." else posixpath.join(expr["root"], relative)
            if expr.get("basename"):
                displayed = posixpath.basename(name)
            if expr.get("sizes"):
                displayed = f"{state[name]['size']}\t{displayed}"
            lines.append(displayed)
        return "".join(line + "\n" for line in lines)
    if op == "names":
        base = absolute(expr["directory"])
        names = [posixpath.basename(name) for name in initial_state(spec) if posixpath.dirname(name) == base]
        if not expr.get("all"):
            names = [name for name in names if not name.startswith(".")]
        if expr.get("dots"):
            names += [".", ".."]
        return "".join(name + ("/" if expr.get("slash") and initial_state(spec).get(base + "/" + name, {}).get("type") == "directory" else "") + "\n" for name in sorted(names))
    if op == "link_target":
        return spec["symlinks"][expr["path"]] + "\n"
    if op == "basename":
        return posixpath.basename(expr["path"]).removesuffix(expr.get("suffix", "")) + "\n"
    if op == "dirname":
        return posixpath.dirname(expr["path"]) + "\n"
    source = expression(expr["source"], spec)
    if op == "slice":
        items = source.encode() if expr.get("bytes") else source.splitlines(keepends=True)
        value = items[expr.get("start", 0):expr.get("stop")]
        return value.decode(errors="replace") if expr.get("bytes") else "".join(value)
    if op == "filter":
        pattern = re.escape(expr["pattern"]) if not expr.get("regex") else expr["pattern"]
        if expr.get("word"):
            pattern = r"(?<![A-Za-z0-9_])(?:" + pattern + r")(?![A-Za-z0-9_])"
        if expr.get("whole"):
            pattern = "^(?:" + pattern + ")$"
        regex = re.compile(pattern, re.ASCII | (re.I if expr.get("ignore_case") else 0))
        lines = []
        for index, line in enumerate(source.splitlines(keepends=True), 1):
            matches = bool(regex.search(line.rstrip("\n")))
            if matches != bool(expr.get("invert")):
                lines.append((f"{index}:" if expr.get("numbered") else "") + line)
        return str(len(lines)) + "\n" if expr.get("count") else "".join(lines)
    if op == "count":
        value = source.count("\n") if expr["unit"] == "lines" else len(re.findall(r"[^ \t\r\n\v\f]+", source)) if expr["unit"] == "words" else len(source.encode())
        return str(value) + "\n"
    if op == "sort":
        lines = source.splitlines()
        def key(line):
            field = line.split(expr.get("delimiter"))[expr["field"] - 1] if expr.get("field") else line
            return (int(field) if expr.get("numeric") else field, line)
        lines = sorted(lines, key=key, reverse=bool(expr.get("reverse")))
        if expr.get("unique"):
            lines = list(dict.fromkeys(lines))
        return "".join(line + "\n" for line in lines)
    if op == "unique":
        groups = []
        for line in source.splitlines():
            if groups and groups[-1][0] == line:
                groups[-1][1] += 1
            else:
                groups.append([line, 1])
        if expr.get("duplicates"):
            groups = [group for group in groups if group[1] > 1]
        if expr.get("single"):
            groups = [group for group in groups if group[1] == 1]
        return "".join((f"{count:7} " if expr.get("counts") else "") + line + "\n" for line, count in groups)
    if op == "replace":
        return re.sub(expr["pattern"], expr["replacement"], source, count=0 if expr.get("global", True) else 1)
    if op == "translate":
        if expr.get("upper"):
            source = source.translate(str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        if expr.get("lower"):
            source = source.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))
        if expr.get("delete"):
            source = source.translate(str.maketrans("", "", expr["delete"]))
        if expr.get("from"):
            source = source.translate(str.maketrans(expr["from"], expr["to"]))
        if expr.get("squeeze"):
            chars = re.escape(expr["squeeze"])
            source = re.sub("([" + chars + "])\\1+", r"\1", source)
        return source
    if op == "fields":
        rows = source.splitlines()[1:] if expr.get("skip_header") else source.splitlines()
        result = []
        for row in rows:
            columns = row.split(expr.get("delimiter"))
            if expr.get("equals") and columns[expr["equals"][0] - 1] != expr["equals"][1]:
                continue
            if expr.get("greater") and int(columns[expr["greater"][0] - 1]) <= expr["greater"][1]:
                continue
            result.append(columns)
        if expr.get("sum"):
            return str(sum(int(row[expr["sum"] - 1]) for row in result)) + "\n"
        return "".join(expr.get("join", "\t").join(row[index - 1] for index in expr["columns"]) + "\n" for row in result)
    if op == "join":
        return expr["separator"].join(source.splitlines()) + "\n"
    if op == "paste":
        right = expression(expr["right"], spec).splitlines()
        left = source.splitlines()
        return "".join(a + expr.get("delimiter", "\t") + b + "\n" for a, b in zip(left, right, strict=True))
    raise ValueError(f"Unknown Extra output expression: {op}")


def expected_state(case, spec):
    state = initial_state(spec)
    for effect in case["expectation"].get("effects", []):
        if effect.get("when_exists") and absolute(effect["when_exists"]) not in state:
            continue
        op = effect["op"]
        if op == "mkdir":
            for name in effect["paths"]:
                current = absolute(name)
                state[current] = {"mode": int(effect.get("mode", "755"), 8), "type": "directory"}
                if effect.get("parents"):
                    current = posixpath.dirname(current)
                    while current.startswith("/workspace/") and current not in state:
                        state[current] = {"mode": 0o755, "type": "directory"}
                        current = posixpath.dirname(current)
        elif op == "write":
            name = absolute(effect["path"])
            content = expression(effect["content"], spec).encode()
            state[name] = {"mode": state.get(name, {}).get("mode", 0o644), "type": "file", "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        elif op in ("copy", "move"):
            for source, target in effect["pairs"]:
                src, dst = absolute(source), absolute(target)
                subtree = {name: dict(info) for name, info in state.items() if name == src or name.startswith(src + "/")}
                if not subtree:
                    raise ValueError(f"Missing oracle source: {src}")
                for name, info in subtree.items():
                    state[dst + name[len(src):]] = info
                    if op == "move":
                        del state[name]
        elif op == "remove":
            names = [absolute(name) for name in effect.get("paths", [])] + (selected(effect["selection"], spec) if effect.get("selection") else [])
            state = {name: info for name, info in state.items() if not any(name == target or name.startswith(target + "/") for target in names)}
        elif op == "chmod":
            for target in effect["paths"]:
                name = absolute(target)
                for path, info in state.items():
                    if path == name or (effect.get("recursive") and path.startswith(name + "/")):
                        if info["type"] != "symlink":
                            info["mode"] = int(effect["mode"], 8)
        elif op == "symlink":
            state[absolute(effect["path"])] = {"mode": 0o777, "type": "symlink", "target": effect["target"]}
        else:
            raise ValueError(f"Unknown Extra state effect: {op}")
    return state


def check_reference(case, spec, outcome):
    from .sandbox import same_stdout
    expected = case["expectation"]
    if outcome["returncode"] != 0 or outcome["stderr"] or not outcome["syntax_ok"] or outcome["timed_out"] or outcome["output_overflow"]:
        raise ValueError(f"Extra reference execution failed: {case['id']}")
    if outcome["cwd"] != absolute(expected.get("cwd", ".")) or outcome["state"] != expected_state(case, spec):
        raise ValueError(f"Extra reference violates intended state/cwd: {case['id']}")
    text = expression(expected.get("stdout", ""), spec)
    if not same_stdout(outcome["stdout"], text, case["comparison"]):
        raise ValueError(f"Extra reference stdout mismatch {case['id']}: {outcome['stdout']!r} != {text!r}")
