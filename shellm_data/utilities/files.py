"""File and path commands."""

from datetime import datetime, timezone
import gzip
import hashlib
import posixpath
import re

from .base import Spec, abspath, quote, quote_args


def _entry(data, mode=0o644):
    return {"mode": mode, "type": "file", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _parent(name):
    return posixpath.dirname(abspath(name))


def _lines(seed, name, count=24):
    return "".join(f"entry {i:02d} variant {seed} from {posixpath.basename(name)}\n" for i in range(1, count + seed))


def _distinct(intent, *names):
    values = [abspath(intent[name]) for name in names]
    if len(set(values)) != len(values):
        raise ValueError(f"{' and '.join(names)} must be different paths")


def _source_destination(intent):
    _distinct(intent, "source", "destination")


def _file_fixture(key):
    def fixture(intent, seed, api):
        api.file(intent[key])
    return fixture


def _no_fixture(intent, seed, api):
    """Pure string commands need no files."""


def _octal_mode(intent):
    if "mode" in intent and not re.fullmatch(r"[0-7]{3}", intent["mode"]):
        raise ValueError("Expected three octal permission digits")


# ln: symbolic link (target string stored literally, as `ln -s` does) or hard link; -f replaces an existing destination.
def ln_render(intent):
    flags = ("s" if intent.get("symbolic") else "") + ("f" if intent.get("force") else "")
    return "ln" + (" -" + flags if flags else "") + " " + quote_args([intent["source"], intent["destination"]])


def ln_fixture(intent, seed, api):
    source = intent["source"]
    if intent.get("symbolic") and not source.startswith("/"):
        # A symbolic target is resolved from the link's directory, so keep the link from dangling.
        source = posixpath.join(posixpath.dirname(intent["destination"]), source)
    api.file(source)
    api.directory(_parent(intent["destination"]))
    if intent.get("force"):
        api.file(intent["destination"], "previous contents\n")


def ln_check(intent, ctx):
    destination = abspath(intent["destination"])
    if intent.get("symbolic"):
        ctx.state[destination] = {"mode": 0o777, "type": "symlink", "target": intent["source"]}
    else:
        ctx.state[destination] = dict(ctx.state[abspath(intent["source"])])
    return "", "exact"


# link: always a hard link.
def link_render(intent):
    return "link " + quote_args([intent["source"], intent["destination"]])


def link_check(intent, ctx):
    ctx.state[abspath(intent["destination"])] = dict(ctx.state[abspath(intent["source"])])
    return "", "exact"


def unlink_render(intent):
    return "unlink " + quote_args([intent["target"]])


def unlink_fixture(intent, seed, api):
    if intent.get("symlink"):
        api.file(posixpath.join(posixpath.dirname(intent["target"]), "original.txt"))
        api.symlink(intent["target"], "original.txt")
    else:
        api.file(intent["target"])


def unlink_check(intent, ctx):
    del ctx.state[abspath(intent["target"])]
    return "", "exact"


def rmdir_render(intent):
    return "rmdir" + (" -p" if intent.get("parents") else "") + " " + quote_args(intent["targets"])


def rmdir_fixture(intent, seed, api):
    for target in intent["targets"]:
        api.directory(target)


def rmdir_validate(intent):
    if intent.get("parents") and (len(intent["targets"]) != 1 or "/" not in intent["targets"][0].strip("/")):
        raise ValueError("rmdir -p needs a single nested target")
    paths = [abspath(t) for t in intent["targets"]]
    if any(a != b and b.startswith(a + "/") for a in paths for b in paths):
        raise ValueError("rmdir targets must not be nested inside each other")


def rmdir_check(intent, ctx):
    for target in intent["targets"]:
        current = abspath(target)
        del ctx.state[current]
        while intent.get("parents"):  # -p also removes the now-empty parents
            current = posixpath.dirname(current)
            if not current.startswith("/workspace/"):
                break
            del ctx.state[current]
    return "", "exact"


# readlink: only the raw link target (the resolved absolute path belongs to realpath). The fixture's
# relative target differs per seed, so neither a hard-coded answer nor a resolved path can pass.
def readlink_render(intent):
    return "readlink " + quote_args([intent["source"]])


def readlink_fixture(intent, seed, api):
    target = f"versions/v{seed + 1}/original.txt"
    api.file(posixpath.join(posixpath.dirname(intent["source"]), target))
    api.symlink(intent["source"], target)


def readlink_check(intent, ctx):
    return ctx.state[abspath(intent["source"])]["target"] + "\n", "exact"


def realpath_render(intent):
    relative = f" --relative-to={quote(intent['relative_to'])}" if "relative_to" in intent else ""
    return "realpath" + relative + " " + quote_args([intent["source"]])


def realpath_fixture(intent, seed, api):
    parts = intent["source"].split("/")
    for index in range(1, len(parts)):  # every raw prefix must exist, e.g. docs in docs/../notes.txt
        if "/".join(parts[:index]):
            api.directory("/".join(parts[:index]))
    if "relative_to" in intent:
        api.directory(intent["relative_to"])
    if intent.get("symlink"):
        api.file(posixpath.join(posixpath.dirname(intent["source"]), "real/original.txt"))
        api.symlink(intent["source"], "real/original.txt")
    else:
        api.file(intent["source"])


def realpath_check(intent, ctx):
    resolved = abspath(intent["source"])
    if intent.get("symlink"):
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(resolved), ctx.state[resolved]["target"]))
    if "relative_to" in intent:
        resolved = posixpath.relpath(resolved, abspath(intent["relative_to"]))
    return resolved + "\n", "exact"


def basename_render(intent):
    return "basename " + quote_args([intent["source"]] + ([intent["suffix"]] if "suffix" in intent else []))


def basename_check(intent, ctx):
    stripped = intent["source"].rstrip("/")
    name = posixpath.basename(stripped) if stripped else "/"
    suffix = intent.get("suffix")
    if suffix and name.endswith(suffix) and name != suffix:
        name = name[:-len(suffix)]
    return name + "\n", "exact"


def dirname_render(intent):
    return "dirname " + quote_args([intent["source"]])


def dirname_check(intent, ctx):
    stripped = intent["source"].rstrip("/")
    if not stripped:
        return "/\n", "exact"
    parent = posixpath.dirname(stripped).rstrip("/")
    return (parent or ("/" if stripped.startswith("/") else ".")) + "\n", "exact"


# stat: metadata that wc and ls do not print directly (byte size belongs to wc).
STAT_FORMATS = {"permissions": "%a", "type": "%F", "owner": "%U", "modified": "%y"}
FIXTURE_MTIME = 1700000000  # the worker pins every fixture mtime
FIXTURE_OWNER = "shellm"  # the worker creates every fixture entry as the image's uid 1000 user


def stat_render(intent):
    return f"stat -c {STAT_FORMATS[intent['format']]} " + quote_args([intent["source"]])


def stat_fixture(intent, seed, api):
    if intent.get("directory"):
        api.file(posixpath.join(intent["source"], "inside.txt"))
    else:
        api.file(intent["source"])


def stat_check(intent, ctx):
    info = ctx.state[abspath(intent["source"])]
    if intent["format"] == "modified":  # %y in the container's TZ=UTC; fixture times have no fraction
        value = datetime.fromtimestamp(FIXTURE_MTIME, timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000000000 +0000")
    else:  # fixture files are never empty, so %F says "regular file", not "regular empty file"
        value = {"permissions": format(info["mode"], "o"), "owner": FIXTURE_OWNER,
                 "type": "directory" if info["type"] == "directory" else "regular file"}[intent["format"]]
    return value + "\n", "exact"


# du: disk usage, not byte size. The container's /workspace is tmpfs, where a regular file uses
# whole 4 KiB pages and a directory uses no blocks (verified with empty, 1-, 4096- and 4097-byte
# files and nested directories). The oracle models exactly that, so it is specific to tmpfs.
PAGE = 4096


def du_render(intent):
    letters = ("s" if intent.get("summary") else "") + ("a" if intent.get("all") else "")
    letters += "h" if intent.get("human") else "k"
    depth = f" --max-depth={intent['max_depth']}" if "max_depth" in intent else ""
    return f"du -{letters}{depth} " + quote_args([intent["source"]])


def du_validate(intent):
    if sum(1 for key in ("summary", "all", "max_depth") if key in intent and intent[key] is not False) > 1:
        raise ValueError("summary, all and max_depth are exclusive")
    if intent.get("max_depth", 1) < 1:
        raise ValueError("max_depth must be positive")
    if intent["source"] != "/" and intent["source"].endswith("/"):
        raise ValueError("Name the directory without a trailing slash")


def du_fixture(intent, seed, api):
    base = intent["source"]
    api.file(posixpath.join(base, "readme.txt"), "r" * (100 + seed))
    api.file(posixpath.join(base, "data", "big.log"), "b" * (4097 + 4096 * seed))
    api.file(posixpath.join(base, "data", "empty.txt"), "")
    api.file(posixpath.join(base, "notes", "today.txt"), "t" * 4096)
    api.file(posixpath.join(base, "notes", "archive", "old.txt"), "o" * 9000)
    api.directory(posixpath.join(base, "cache"))


def human_size(count):
    """GNU -h output: powers of 1024, rounded up, with one decimal below 10."""
    if count < 1024:
        return str(count)
    exponent = 1
    while -(-count // 1024 ** exponent) >= 1024:
        exponent += 1
    scale = 1024 ** exponent
    tenths = -(-count * 10 // scale)
    return (f"{tenths // 10}.{tenths % 10}" if tenths < 100 else str(-(-count // scale))) + "KMGTPE"[exponent - 1]


def du_check(intent, ctx):
    base = abspath(intent["source"])
    inside = {name: info for name, info in ctx.state.items() if name == base or name.startswith(base + "/")}
    inside.setdefault(base, {"type": "directory"})
    if any(info["type"] not in ("file", "directory") for info in inside.values()):
        raise ValueError("Only regular files and directories are modelled")

    def usage(name):
        return sum(-(-info["size"] // PAGE) * PAGE for path, info in inside.items()
                   if info["type"] == "file" and (path == name or path.startswith(name + "/")))

    rows = []
    for name, info in inside.items():
        depth = 0 if name == base else name[len(base):].count("/")
        if name == base:
            shown = True
        elif intent.get("summary"):
            shown = False
        elif info["type"] == "file":
            shown = bool(intent.get("all"))
        else:
            shown = depth <= intent.get("max_depth", depth)
        if shown:
            size = usage(name)
            label = intent["source"] + name[len(base):]
            rows.append((human_size(size) if intent.get("human") else str(size // 1024)) + "\t" + label + "\n")
    return "".join(rows), "lines"


def truncate_render(intent):
    return f"truncate -s {intent['size']} " + quote_args([intent["target"]])


def truncate_check(intent, ctx):
    data = ctx.read(intent["target"]).encode()
    size = intent["size"]
    ctx.state[abspath(intent["target"])] = _entry(data[:size].ljust(size, b"\0"))
    return "", "exact"


def install_render(intent):
    flag = " -D" if intent.get("create_dirs") else ""
    return f"install{flag} -m {intent['mode']} " + quote_args([intent["source"], intent["destination"]])


def install_fixture(intent, seed, api):
    api.file(intent["source"])
    if not intent.get("create_dirs"):
        api.directory(_parent(intent["destination"]))


def install_validate(intent):
    _octal_mode(intent)
    _distinct(intent, "source", "destination")


def install_check(intent, ctx):
    destination = abspath(intent["destination"])
    if intent.get("create_dirs"):  # -D creates the missing leading directories
        current = posixpath.dirname(destination)
        while current.startswith("/workspace/") and current not in ctx.state:
            ctx.state[current] = {"mode": 0o755, "type": "directory"}
            current = posixpath.dirname(current)
    ctx.state[destination] = _entry(ctx.read(intent["source"]).encode(), int(intent["mode"], 8))
    return "", "exact"


def mkfifo_render(intent):
    return "mkfifo" + (f" -m {intent['mode']}" if "mode" in intent else "") + " " + quote_args(intent["targets"])


def mkfifo_fixture(intent, seed, api):
    for target in intent["targets"]:
        api.directory(_parent(target))


def mkfifo_check(intent, ctx):
    for target in intent["targets"]:
        ctx.state[abspath(target)] = {"mode": int(intent.get("mode", "644"), 8), "type": "special"}
    return "", "exact"


# shred: only the removing form is modelled; plain `shred` leaves random content behind.
def shred_render(intent):
    return "shred" + (f" -n {intent['passes']}" if "passes" in intent else "") + " -u " + quote_args([intent["target"]])


def shred_validate(intent):
    if intent.get("passes", 1) < 1:
        raise ValueError("passes must be positive")


def shred_check(intent, ctx):
    del ctx.state[abspath(intent["target"])]
    return "", "exact"


UNITS = {"K": 1024, "M": 1024 * 1024}


def fallocate_render(intent):
    return f"fallocate -l {intent['size']}{intent.get('unit', '')} " + quote_args([intent["target"]])


def fallocate_fixture(intent, seed, api):
    api.directory(_parent(intent["target"]))


def fallocate_validate(intent):
    if not 1 <= intent["size"] * UNITS.get(intent.get("unit"), 1) <= 4 * 1024 * 1024:
        raise ValueError("size must be positive and at most 4 MiB")


def fallocate_check(intent, ctx):
    ctx.state[abspath(intent["target"])] = _entry(bytes(intent["size"] * UNITS.get(intent.get("unit"), 1)))
    return "", "exact"


def gzip_render(intent):
    flags = [flag for key, flag in (("recursive", "-r"), ("keep", "-k"), ("best", "-9")) if intent.get(key)]
    return "gzip " + "".join(flag + " " for flag in flags) + quote_args([intent["source"]])


def gzip_fixture(intent, seed, api):
    if intent.get("recursive"):
        api.file(posixpath.join(intent["source"], "first.txt"))
        api.file(posixpath.join(intent["source"], "nested", "second.txt"))
    else:
        api.file(intent["source"])


def gzip_check(intent, ctx):
    # Python's deflate output differs from gzip's bytes, so each new .gz file is an opaque
    # output. We require a regular 0644 file of plausible size (header and trailer alone are
    # 18 bytes, and the repetitive fixture text must compress) and adopt its recorded
    # size/sha256 into the expected state. Everything else (originals kept or removed, no
    # other changes) is still checked strictly. The compressed bytes themselves are not verified.
    source = abspath(intent["source"])
    if intent.get("recursive"):
        originals = [name for name, info in ctx.state.items() if name.startswith(source + "/") and info["type"] == "file"]
    else:
        originals = [source]
    for original in originals:
        packed = ctx.outcome["state"].get(original + ".gz")
        if not packed or packed.get("type") != "file" or packed.get("mode") != 0o644 \
                or not 18 < packed.get("size", 0) < ctx.state[original]["size"]:
            raise ValueError(f"gzip did not produce a plausible {original}.gz: {packed}")
        ctx.state[original + ".gz"] = dict(packed)
        if not intent.get("keep"):
            del ctx.state[original]
    return "", "exact"


def gz_validate(intent):
    if not intent["source"].endswith(".gz") or intent["source"] == ".gz":
        raise ValueError("source must be a .gz file")


def gz_fixture(intent, seed, api):
    api.binary(intent["source"], gzip.compress(_lines(seed, intent["source"][:-3]).encode(), mtime=0))


def gunzip_render(intent):
    if "destination" in intent:
        return "gunzip -c " + quote_args([intent["source"]]) + " > " + quote(intent["destination"])
    return "gunzip" + (" -k " if intent.get("keep") else " ") + quote_args([intent["source"]])


def gunzip_fixture(intent, seed, api):
    gz_fixture(intent, seed, api)
    if "destination" in intent:
        api.directory(_parent(intent["destination"]))


def gunzip_validate(intent):
    gz_validate(intent)
    if "destination" in intent:
        if intent.get("keep"):
            raise ValueError("keep and destination are exclusive")
        _source_destination(intent)


def gunzip_check(intent, ctx):
    source = abspath(intent["source"])
    data = gzip.decompress(ctx.binaries[source])
    if "destination" in intent:
        ctx.state[abspath(intent["destination"])] = _entry(data)
        return "", "exact"
    ctx.state[source[:-3]] = _entry(data)
    if not intent.get("keep"):
        del ctx.state[source]
    return "", "exact"


def zcat_render(intent):
    return "zcat " + quote_args([intent["source"]]) + (f" | head -n {intent['lines']}" if "lines" in intent else "")


def zcat_validate(intent):
    gz_validate(intent)
    if intent.get("lines", 1) < 1:
        raise ValueError("lines must be positive")


def zcat_check(intent, ctx):
    text = gzip.decompress(ctx.binaries[abspath(intent["source"])]).decode()
    if "lines" in intent:
        text = "".join(text.splitlines(keepends=True)[:intent["lines"]])
    return text, "exact"


# dd: copy blocks from one file to another (zero-filled new files belong to fallocate).
def dd_render(intent):
    extras = "".join(f" {key}={intent[key]}" for key in ("skip", "seek") if key in intent)
    return (f"dd if={quote(intent['source'])} of={quote(intent['destination'])} "
            f"bs={intent['block_size']}{extras} count={intent['count']}"
            f"{' conv=notrunc' if intent.get('notrunc') else ''} status=none")


def dd_data(seed):
    return bytes((i * 7 + seed) % 251 for i in range(4096))


def dd_existing(seed):
    return bytes((i * 13 + 5 + seed) % 256 for i in range(4096))


def dd_fixture(intent, seed, api):
    api.binary(intent["source"], dd_data(seed))
    if intent.get("notrunc"):  # patching in place needs an existing output with different bytes
        api.binary(intent["destination"], dd_existing(seed))
    else:
        api.directory(_parent(intent["destination"]))


def dd_validate(intent):
    size, skip, seek = intent["block_size"], intent.get("skip", 0), intent.get("seek", 0)
    if size < 1 or intent["count"] < 1:
        raise ValueError("block_size and count must be positive")
    if abspath(intent["source"]).startswith("/dev/"):
        raise ValueError("Device sources are not modelled; zero-filled new files belong to fallocate")
    if (skip + intent["count"]) * size > 4096:
        raise ValueError("dd must read within the 4096-byte fixture")
    if (seek + intent["count"]) * size > 1024 * 1024:
        raise ValueError("dd output must stay below 1 MiB")
    _distinct(intent, "source", "destination")


def dd_check(intent, ctx):
    size, count = intent["block_size"], intent["count"]
    skip, offset = intent.get("skip", 0) * size, intent.get("seek", 0) * size
    chunk = ctx.binaries[abspath(intent["source"])][skip:skip + size * count]
    existing = ctx.binaries[abspath(intent["destination"])] if intent.get("notrunc") else b""
    # Without conv=notrunc the output is cut at the seek offset; with it, bytes after the copy survive.
    data = existing[:offset].ljust(offset, b"\0") + chunk + existing[offset + len(chunk):]
    ctx.state[abspath(intent["destination"])] = _entry(data)
    return "", "exact"


SPECS = {
    "ln": Spec({"source": "path", "destination": "path", "symbolic": "bool", "force": "bool"},
               frozenset({"source", "destination"}), ln_render, ln_fixture, ln_check, extra_validation=_source_destination),
    "link": Spec({"source": "path", "destination": "path"}, frozenset({"source", "destination"}),
                 link_render, ln_fixture, link_check, extra_validation=_source_destination),
    "unlink": Spec({"target": "path", "symlink": "bool"}, frozenset({"target"}), unlink_render, unlink_fixture, unlink_check),
    "rmdir": Spec({"targets": "paths", "parents": "bool"}, frozenset({"targets"}), rmdir_render, rmdir_fixture, rmdir_check,
                  extra_validation=rmdir_validate),
    "readlink": Spec({"source": "path"}, frozenset({"source"}), readlink_render, readlink_fixture, readlink_check),
    "realpath": Spec({"source": "path", "relative_to": "path", "symlink": "bool"}, frozenset({"source"}),
                     realpath_render, realpath_fixture, realpath_check),
    "basename": Spec({"source": "path", "suffix": "text"}, frozenset({"source"}),
                     basename_render, _no_fixture, basename_check),
    "dirname": Spec({"source": "path"}, frozenset({"source"}), dirname_render, _no_fixture, dirname_check),
    "stat": Spec({"source": "path", "format": "enum:permissions|type|owner|modified", "directory": "bool"},
                 frozenset({"source", "format"}), stat_render, stat_fixture, stat_check),
    "du": Spec({"source": "path", "human": "bool", "summary": "bool", "all": "bool", "max_depth": "int"},
               frozenset({"source"}), du_render, du_fixture, du_check, extra_validation=du_validate),
    "truncate": Spec({"target": "path", "size": "int"}, frozenset({"target", "size"}),
                     truncate_render, _file_fixture("target"), truncate_check),
    "install": Spec({"source": "path", "destination": "path", "mode": "text", "create_dirs": "bool"},
                    frozenset({"source", "destination", "mode"}), install_render, install_fixture, install_check,
                    extra_validation=install_validate),
    "mkfifo": Spec({"targets": "paths", "mode": "text"}, frozenset({"targets"}), mkfifo_render, mkfifo_fixture, mkfifo_check,
                   extra_validation=_octal_mode),
    "shred": Spec({"target": "path", "passes": "int"}, frozenset({"target"}), shred_render, _file_fixture("target"),
                  shred_check, extra_validation=shred_validate),
    "fallocate": Spec({"target": "path", "size": "int", "unit": "enum:K|M"}, frozenset({"target", "size"}),
                      fallocate_render, fallocate_fixture, fallocate_check, extra_validation=fallocate_validate),
    "gzip": Spec({"source": "path", "keep": "bool", "recursive": "bool", "best": "bool"}, frozenset({"source"}),
                 gzip_render, gzip_fixture, gzip_check),
    "gunzip": Spec({"source": "path", "keep": "bool", "destination": "path"}, frozenset({"source"}),
                   gunzip_render, gunzip_fixture, gunzip_check, extra_validation=gunzip_validate),
    "zcat": Spec({"source": "path", "lines": "int"}, frozenset({"source"}), zcat_render, gz_fixture, zcat_check,
                 extra_validation=zcat_validate),
    "dd": Spec({"source": "path", "destination": "path", "block_size": "int", "count": "int", "skip": "int", "seek": "int",
                "notrunc": "bool"},
               frozenset({"source", "destination", "block_size", "count"}), dd_render, dd_fixture, dd_check,
               extra_validation=dd_validate),
}
