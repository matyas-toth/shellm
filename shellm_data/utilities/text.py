"""Text and stream commands. Exemplar: `sort`."""

import base64
import hashlib
import posixpath
import re

from .base import Spec, abspath, quote, quote_args


# --- shared helpers --------------------------------------------------------------------------------------


def lines_of(ctx, name):
    return ctx.read(name).splitlines()


def joined(lines):
    return "".join(line + "\n" for line in lines)


def file_entry(content):
    data = content.encode() if isinstance(content, str) else content
    return {"mode": 0o644, "type": "file", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def single_char(value, name="delimiter"):
    if len(value) != 1 or value == "\\":
        raise ValueError(f"{name} must be one character other than a backslash")


def exactly_one(intent, names):
    if sum(name in intent for name in names) != 1:
        raise ValueError(f"Exactly one of {names} is required")


def read_bytes(ctx, name):
    path = abspath(name)
    return ctx.binaries[path] if path in ctx.binaries else ctx.read(name).encode()


# --- sort ------------------------------------------------------------------------------------------------

SORT_ROWS = [("alice", 30, "oslo"), ("bob", 4, "lima"), ("carol", 100, "rome"), ("dave", 30, "kyiv"),
             ("erin", 25, "bern"), ("frank", 7, "lima")]


def sort_render(intent):
    flags = "".join(letter for key, letter in (("reverse", "r"), ("numeric", "n"), ("unique", "u")) if intent.get(key))
    key = f" -t{quote(intent['delimiter'])} -k{intent['key']},{intent['key']}" if "key" in intent else ""
    return "sort" + key + (" -" + flags if flags else "") + " " + quote_args([intent["source"]])


def sort_validate(intent):
    if ("key" in intent) != ("delimiter" in intent):
        raise ValueError("key and delimiter go together")
    if "key" in intent:
        single_char(intent["delimiter"])
        if intent["key"] < 1 or intent.get("unique"):
            raise ValueError("key starts at 1 and cannot be combined with unique")


def sort_fixture(intent, seed, api):
    if "key" in intent:
        text = "".join(intent["delimiter"].join((name, str(score), city)) + "\n" for name, score, city in SORT_ROWS)
    elif intent.get("numeric"):
        text = "10\n9\n100\n1\n9\n25\n"
    else:
        text = "pear\napple\nbanana\napple\ncherry\nBanana\n"
    api.file(intent["source"], text)


def sort_check(intent, ctx):
    lines = ctx.read(intent["source"]).splitlines()
    if "key" in intent:
        def key(line):
            field = line.split(intent["delimiter"])[intent["key"] - 1]
            return (int(field) if intent.get("numeric") else field.encode(), line.encode())
        return joined(sorted(lines, key=key, reverse=bool(intent.get("reverse")))), "exact"
    key = (lambda line: int(line)) if intent.get("numeric") else (lambda line: line.encode())
    ordered = sorted(lines, key=key, reverse=bool(intent.get("reverse")))
    if intent.get("unique"):
        seen, unique = set(), []
        for line in ordered:
            if key(line) not in seen:
                seen.add(key(line))
                unique.append(line)
        ordered = unique
    return joined(ordered), "exact"


# --- awk -------------------------------------------------------------------------------------------------


def awk_program(intent):
    if "sum_field" in intent:
        return f"{{s+=${intent['sum_field']}}} END {{print s}}"
    condition = f"${intent['where_field']} == \"{intent['where_value']}\"" if "where_field" in intent else ""
    action = f"{{print ${intent['field']}}}" if "field" in intent else ""
    return f"{condition} {action}".strip()


def awk_render(intent):
    separator = " -F" + quote(intent["delimiter"]) if "delimiter" in intent else ""
    return f"awk{separator} " + quote(awk_program(intent)) + " " + quote(intent["source"])


def awk_validate(intent):
    for name in ("field", "where_field", "sum_field"):
        if name in intent and intent[name] < 1:
            raise ValueError(f"{name} starts at 1")
    if "delimiter" in intent:
        single_char(intent["delimiter"])
        if intent["delimiter"] == " ":
            raise ValueError("delimiter must not be a space")
    if intent["source"].startswith("-"):
        raise ValueError("source must not start with a dash")
    if ("where_field" in intent) != ("where_value" in intent) or any(c in intent.get("where_value", "") for c in '"\\'):
        raise ValueError("where_field and a plain where_value go together")
    if "sum_field" in intent:
        if {"field", "where_field"} & intent.keys():
            raise ValueError("sum_field cannot be combined with field or where_field")
    elif not {"field", "where_field"} & intent.keys():
        raise ValueError("Nothing to print")
    elif "delimiter" in intent and "where_field" not in intent:
        raise ValueError("Printing fields split on a single-character delimiter belongs to cut")


def awk_cell(row, column, delimiter):
    return f"c{column}{' ' if delimiter else ''}r{row}"


def awk_fixture(intent, seed, api):
    delimiter = intent.get("delimiter")
    joiner = delimiter or " "
    columns = max(4, *(intent.get(name, 0) for name in ("field", "where_field", "sum_field")))
    if "sum_field" in intent:
        rows = [[str(10 + (row * 7 + column * 13) % 90) for column in range(1, columns + 1)] for row in range(6)]
    elif "where_field" in intent:
        rows = []
        for row in range(6):
            cells = [awk_cell(row, column, delimiter) for column in range(1, columns + 1)]
            cells[intent["where_field"] - 1] = intent["where_value"] if row % 2 == 0 else f"other{row}"
            if row % 2:  # decoys: the wanted value sits in a different column
                cells[intent["where_field"] % columns] = intent["where_value"]
            rows.append(cells)
    else:
        # Irregular runs of spaces and tabs (and leading blanks) separate the columns, so splitting on one space is wrong.
        rows = [[f"name{row}", str(20 + row * 7), f"city{row}"] + [f"x{row}{column}" for column in range(4, columns + 1)]
                for row in range(5)]
        api.file(intent["source"], "".join(("  " if row % 2 else "") + (" \t  " if row % 3 == 0 else "   ").join(cells) + "\n"
                                           for row, cells in enumerate(rows)))
        return
    api.file(intent["source"], joined(joiner.join(cells) for cells in rows))


def awk_check(intent, ctx):
    delimiter, out, total = intent.get("delimiter"), [], 0
    for line in lines_of(ctx, intent["source"]):
        parts = line.split(delimiter) if delimiter else line.split()
        cell = lambda n: parts[n - 1] if n <= len(parts) else ""
        if "sum_field" in intent:
            total += int(cell(intent["sum_field"]) or 0)
        elif "where_field" in intent and cell(intent["where_field"]) != intent["where_value"]:
            continue
        else:
            out.append(cell(intent["field"]) if "field" in intent else line)
    return (f"{total}\n" if "sum_field" in intent else joined(out)), "exact"


# --- sed -------------------------------------------------------------------------------------------------


def sed_expression(intent):
    if "pattern" in intent:
        return f"s/{intent['pattern']}/{intent['replacement']}/" + ("g" if intent.get("global") else "")
    if "delete_prefix" in intent:
        return f"/^{intent['delete_prefix']}/d"
    return f"{intent['start']},{intent['end']}p" if "end" in intent else f"{intent['start']}p"


def sed_render(intent):
    # The sed program is always single-quoted; validation keeps quotes and metacharacters out of it.
    return ("sed" + (" -i" if intent.get("in_place") else "") + (" -n" if "start" in intent else "") + " '"
            + sed_expression(intent) + "' " + quote_args([intent["source"]]))


def sed_validate(intent):
    exactly_one(intent, ("pattern", "delete_prefix", "start"))
    if ("pattern" in intent) != ("replacement" in intent):
        raise ValueError("pattern and replacement go together")
    for name in ("pattern", "replacement", "delete_prefix"):
        if any(c in intent.get(name, "") for c in "/\\&.*[]^$\t'"):
            raise ValueError(f"{name} must be plain text without sed metacharacters or quotes")
    if "global" in intent and "pattern" not in intent:
        raise ValueError("global only applies to a substitution")
    if intent.get("in_place") and "start" in intent:
        raise ValueError("in_place does not apply to printing a range")
    if "end" in intent and "start" not in intent:
        raise ValueError("end needs start")
    if "start" in intent and not 1 <= intent["start"] <= intent.get("end", intent["start"]):
        raise ValueError("Invalid line range")


def sed_fixture(intent, seed, api):
    if "pattern" in intent:
        p = intent["pattern"]
        lines = [f"{p}: disk {p} on sda", "ok: service started", f"{p.upper()}: not a {p}", "warn: low memory", f"{p} {p} {p}"]
    elif "delete_prefix" in intent:
        p = intent["delete_prefix"]
        # Decoys: the prefix in the middle of a line, after indentation, and an empty line.
        lines = [f"{p} first comment", "port = 8080", f"  {p} indented note stays", f"path = /srv {p} trailing note",
                 f"{p}compact comment", "", "mode = fast"]
    else:
        lines = [f"line {i} of the chapter" for i in range(1, max(10, intent.get("end", intent["start"]) + 3) + 1)]
    api.file(intent["source"], joined(lines))


def sed_check(intent, ctx):
    lines = lines_of(ctx, intent["source"])
    if "pattern" in intent:
        limit = -1 if intent.get("global") else 1
        lines = [line.replace(intent["pattern"], intent["replacement"], limit) for line in lines]
    elif "delete_prefix" in intent:
        lines = [line for line in lines if not line.startswith(intent["delete_prefix"])]
    else:
        return joined(lines[intent["start"] - 1:intent.get("end", intent["start"])]), "exact"
    if intent.get("in_place"):
        ctx.state[abspath(intent["source"])] = file_entry(joined(lines))
        return "", "exact"
    return joined(lines), "exact"


# --- uniq ------------------------------------------------------------------------------------------------


def uniq_render(intent):
    flags = "".join(letter for key, letter in (("count", "c"), ("duplicates", "d"), ("unique", "u")) if intent.get(key))
    return "uniq" + (" -" + flags if flags else "") + " " + quote_args([intent["source"]])


def uniq_validate(intent):
    if intent.get("duplicates") and intent.get("unique"):
        raise ValueError("duplicates and unique are exclusive")


def uniq_fixture(intent, seed, api):
    api.file(intent["source"], "home\nhome\nabout\nabout\nabout\ncontact\nhome\npricing\npricing\nblog\n")


def uniq_check(intent, ctx):
    runs = []
    for line in lines_of(ctx, intent["source"]):
        if runs and runs[-1][0] == line:
            runs[-1][1] += 1
        else:
            runs.append([line, 1])
    if intent.get("duplicates"):
        runs = [run for run in runs if run[1] > 1]
    if intent.get("unique"):
        runs = [run for run in runs if run[1] == 1]
    return joined(f"{n:7d} {line}" if intent.get("count") else line for line, n in runs), "exact"


# --- cut -------------------------------------------------------------------------------------------------

CUT_RANGE = re.compile(r"([1-9][0-9]*)(?:-([1-9][0-9]*))?")


def cut_render(intent):
    if "characters" in intent:
        return f"cut -c{intent['characters']} " + quote_args([intent["source"]])
    delimiter = f" -d{quote(intent['delimiter'])}" if "delimiter" in intent else ""
    return f"cut{delimiter} -f{','.join(map(str, intent['fields']))} " + quote_args([intent["source"]])


def cut_validate(intent):
    exactly_one(intent, ("fields", "characters"))
    if "characters" in intent:
        match = CUT_RANGE.fullmatch(intent["characters"])
        if not match or int(match.group(2) or match.group(1)) < int(match.group(1)) or int(match.group(2) or match.group(1)) > 20:
            raise ValueError("characters must be N or N-M with N <= M <= 20")
        if "delimiter" in intent:
            raise ValueError("delimiter only applies to fields")
    else:
        if "delimiter" in intent:
            single_char(intent["delimiter"])
        if intent["fields"] != sorted(set(intent["fields"])):
            raise ValueError("fields must be strictly increasing")


def cut_fixture(intent, seed, api):
    if "characters" in intent:
        lines = [f"{2020 + i}-{i + 3:02d}-{10 + i} user{i} signed in from a new device" for i in range(5)]
    else:
        delimiter = intent.get("delimiter", "\t")
        columns = max(intent["fields"]) + 1
        lines = [delimiter.join(f"r{i}{'' if delimiter == ' ' else ' '}c{j}" for j in range(1, columns + 1)) for i in range(4)]
        lines.insert(2, "a line without any delimiter")
    api.file(intent["source"], joined(lines))


def cut_check(intent, ctx):
    out = []
    if "characters" in intent:
        match = CUT_RANGE.fullmatch(intent["characters"])
        start, end = int(match.group(1)), int(match.group(2) or match.group(1))
        return joined(line[start - 1:end] for line in lines_of(ctx, intent["source"])), "exact"
    d = intent.get("delimiter", "\t")
    for line in lines_of(ctx, intent["source"]):
        if d not in line:
            out.append(line)
            continue
        parts = line.split(d)
        out.append(d.join(parts[i - 1] for i in intent["fields"] if i <= len(parts)))
    return joined(out), "exact"


# --- tr --------------------------------------------------------------------------------------------------

TR_ITEM = r"[A-Za-z0-9 ]-[A-Za-z0-9 ]|[A-Za-z0-9 .,:;_]"


def tr_expand(spec):
    if not re.fullmatch(f"(?:{TR_ITEM})+", spec):
        raise ValueError(f"Unsupported tr set {spec!r}")
    chars = []
    for item in re.findall(TR_ITEM, spec):
        if len(item) == 3:
            if item[0] > item[2]:
                raise ValueError(f"Reversed tr range {item!r}")
            chars.extend(chr(c) for c in range(ord(item[0]), ord(item[2]) + 1))
        else:
            chars.append(item)
    return chars


def tr_validate(intent):
    source = tr_expand(intent["from"])
    if len(set(source)) != len(source):
        raise ValueError("tr source set must not repeat characters")
    if intent.get("delete") or intent.get("squeeze"):
        if "to" in intent or (intent.get("delete") and intent.get("squeeze")):
            raise ValueError("delete and squeeze take only the source set")
    elif "to" not in intent or len(tr_expand(intent["to"])) != len(source):
        raise ValueError("tr sets must have equal length")


def tr_render(intent):
    flag = " -d" if intent.get("delete") else " -s" if intent.get("squeeze") else ""
    sets = quote(intent["from"]) + (" " + quote(intent["to"]) if "to" in intent else "")
    return f"tr{flag} {sets} < {quote(intent['source'])}"


def tr_fixture(intent, seed, api):
    api.file(intent["source"], "Hello  World!!  Aaa bbb  cc 2024\nTHE  Quick   brown fox\n   leading spaces  here\n"
                               "Meeting notes: project alpha, see Dr. Smith about the Q3 plan\n")


def tr_check(intent, ctx):
    text, chars = ctx.read(intent["source"]), tr_expand(intent["from"])
    if intent.get("delete"):
        return "".join(c for c in text if c not in chars), "exact"
    if intent.get("squeeze"):
        out = ""
        for c in text:
            if not (out and out[-1] == c and c in chars):
                out += c
        return out, "exact"
    table = dict(zip(chars, tr_expand(intent["to"])))
    return "".join(table.get(c, c) for c in text), "exact"


# --- paste -----------------------------------------------------------------------------------------------

PASTE_POOLS = (["alpha", "bravo", "charlie", "delta", "echo"], ["81", "77", "92", "65", "70"], ["red", "green", "blue", "gold", "gray"])
PASTE_COUNTS = (5, 4, 3, 5)


def paste_render(intent):
    delimiter = " -d" + quote(intent["delimiter"]) if "delimiter" in intent else ""
    return "paste" + (" -s" if intent.get("serial") else "") + delimiter + " " + quote_args(intent["sources"])


def paste_validate(intent):
    if len(intent["sources"]) < (1 if intent.get("serial") else 2):
        raise ValueError("paste needs at least two sources (one when serial)")
    if "delimiter" in intent:
        single_char(intent["delimiter"])


def paste_fixture(intent, seed, api):
    for index, name in enumerate(intent["sources"]):
        api.file(name, joined(PASTE_POOLS[index % 3][:PASTE_COUNTS[index % 4]]))


def paste_check(intent, ctx):
    columns = [lines_of(ctx, name) for name in intent["sources"]]
    d = intent.get("delimiter", "\t")
    if intent.get("serial"):
        return joined(d.join(column) for column in columns), "exact"
    return joined(d.join(column[i] if i < len(column) else "" for column in columns)
                  for i in range(max(map(len, columns)))), "exact"


# --- nl --------------------------------------------------------------------------------------------------


def nl_render(intent):
    options = ((" -b a" if intent.get("all") else "") + (f" -w {intent['width']}" if "width" in intent else "")
               + (f" -s {quote(intent['separator'])}" if "separator" in intent else "")
               + (f" -v {intent['start']}" if "start" in intent else ""))
    return "nl" + options + " " + quote_args([intent["source"]])


def nl_validate(intent):
    if intent.get("width", 1) < 1:
        raise ValueError("width must be positive")
    if "separator" in intent and "\\" in intent["separator"]:
        raise ValueError("separator must not contain a backslash")


def nl_fixture(intent, seed, api):
    api.file(intent["source"], "roses are red\n\nviolets are blue\n\n\nsugar is sweet\n")


def nl_check(intent, ctx):
    number, out = intent.get("start", 1), []
    width, separator = intent.get("width", 6), intent.get("separator", "\t")
    for line in lines_of(ctx, intent["source"]):
        if line or intent.get("all"):
            out.append(f"{number:>{width}}{separator}{line}")
            number += 1
        else:
            out.append(" " * (width + len(separator)))
    return joined(out), "exact"


# --- tac / rev -------------------------------------------------------------------------------------------

TAC_TEXTS = ("cd src\nmake\nmake test\nmake\ngit status\n", "one\ntwo\nthree\nfour\n", "first\nsecond\nsecond\nthird\n")
REV_TEXTS = ("stressed\nlevel\nhello world\nabc123\n", "noon\nDesserts and 42\nxyz\n", "a b c\nracecar\nPython 3\n")


def multi_source_spec(command, texts, transform):
    def render(intent):
        return command + " " + quote_args(intent.get("sources") or [intent["source"]])

    def fixture(intent, seed, api):
        for index, name in enumerate(intent.get("sources") or [intent["source"]]):
            api.file(name, texts[index % len(texts)])

    def check(intent, ctx):
        return "".join(transform(lines_of(ctx, name)) for name in intent.get("sources") or [intent["source"]]), "exact"

    return Spec({"source": "path", "sources": "paths"}, frozenset(), render, fixture, check,
                extra_validation=lambda intent: exactly_one(intent, ("source", "sources")))


# --- fold ------------------------------------------------------------------------------------------------


def fold_render(intent):
    return "fold" + (" -s" if intent.get("spaces") else "") + (f" -w {intent['width']}" if "width" in intent else "") + " " + quote_args([intent["source"]])


def fold_validate(intent):
    if intent.get("width", 1) < 1:
        raise ValueError("width must be positive")


def fold_fixture(intent, seed, api):
    api.file(intent["source"], "The quick brown fox jumps over the lazy dog near the quiet river bank while the morning sun "
                               "climbs slowly above the distant hills and the village begins to wake up for another long day\n\n"
                               "Short line\nPack my box with five dozen liquor jugs and then rest for a while\n")


def fold_check(intent, ctx):
    width, out = intent.get("width", 80), []
    for line in lines_of(ctx, intent["source"]):
        rest = line
        while len(rest) > width:
            # With -s break after the last space inside the window; otherwise (or without a space) cut at the width.
            cut = (rest[:width].rfind(" ") + 1 if intent.get("spaces") else 0) or width
            out.append(rest[:cut])
            rest = rest[cut:]
        out.append(rest)
    return joined(out), "exact"


# --- expand / unexpand -----------------------------------------------------------------------------------


def expand_render(intent):
    return ("expand" + (" -i" if intent.get("initial") else "") + (f" -t {intent['tabstop']}" if "tabstop" in intent else "")
            + " " + quote_args([intent["source"]]))


def expand_validate(intent):
    if intent.get("tabstop", 1) < 1:
        raise ValueError("tabstop must be positive")


def expand_fixture(intent, seed, api):
    api.file(intent["source"], "\tindent\n a\tb\nabc\tdef\tg\nno tabs here\n\t\ttwo tabs\tinner\n  \tmixed lead\n")


def expand_check(intent, ctx):
    stop, out = intent.get("tabstop", 8), []
    for line in lines_of(ctx, intent["source"]):
        text, leading = "", True
        for c in line:
            if c == "\t" and (leading or not intent.get("initial")):
                text += " " * (stop - len(text) % stop)
            else:
                text += c
                leading = leading and c in " \t"
        out.append(text)
    return joined(out), "exact"


def unexpand_render(intent):
    return ("unexpand" + (" -a" if intent.get("all") else "") + (f" -t {intent['tabstop']}" if "tabstop" in intent else "")
            + " " + quote_args([intent["source"]]))


def unexpand_validate(intent):
    if intent.get("tabstop", 2) < 2:
        raise ValueError("tabstop must be at least 2")
    if "tabstop" in intent and "all" in intent:
        raise ValueError("tabstop already converts every blank run")


def unexpand_fixture(intent, seed, api):
    api.file(intent["source"], "        eight spaces\n                sixteen spaces\n    four spaces\n"
                               "          ten spaces\nx        inner spaces\nab    cd      ef  gh\nnine         spaces nine\n")


def unexpand_line(line, stop, everywhere):
    out, column, pending, leading = [], 0, 0, True
    for index, c in enumerate(line):
        if c in " \t" and (everywhere or leading):
            column = column + 1 if c == " " else (column // stop + 1) * stop
            pending += 1
            if column % stop == 0:
                # A lone space reaching a tab stop stays a space unless another blank follows it.
                lone = pending == 1 and c == " " and line[index + 1:index + 2] not in (" ", "\t")
                out.append(" " if lone else "\t")
                pending = 0
        else:
            out.append(" " * pending + c)
            pending, column, leading = 0, column + 1, False
    return "".join(out) + " " * pending


def unexpand_check(intent, ctx):
    everywhere = bool(intent.get("all") or "tabstop" in intent)
    return joined(unexpand_line(line, intent.get("tabstop", 8), everywhere) for line in lines_of(ctx, intent["source"])), "exact"


# --- comm ------------------------------------------------------------------------------------------------

COMM_FLAGS = {"common": " -12", "first_only": " -23", "second_only": " -13", "all": ""}


def comm_render(intent):
    return f"comm{COMM_FLAGS[intent['show']]} " + quote_args(intent["sources"])


def comm_validate(intent):
    if len(intent["sources"]) != 2:
        raise ValueError("comm compares exactly two sources")


def comm_fixture(intent, seed, api):
    api.file(intent["sources"][0], "apple\nbanana\ncherry\ndate\nfig\n")
    api.file(intent["sources"][1], "banana\ncherry\nelder\nfig\ngrape\n")


def comm_check(intent, ctx):
    first, second = (sorted(lines_of(ctx, name)) for name in intent["sources"])
    rows, i, j = [], 0, 0
    while i < len(first) or j < len(second):
        if j == len(second) or (i < len(first) and first[i] < second[j]):
            rows.append((1, first[i]))
            i += 1
        elif i == len(first) or second[j] < first[i]:
            rows.append((2, second[j]))
            j += 1
        else:
            rows.append((3, first[i]))
            i += 1
            j += 1
    if intent["show"] == "all":
        return joined("\t" * (column - 1) + line for column, line in rows), "exact"
    column = {"common": 3, "first_only": 1, "second_only": 2}[intent["show"]]
    return joined(line for c, line in rows if c == column), "exact"


# --- od --------------------------------------------------------------------------------------------------

OD_ESCAPES = {0: "\\0", 7: "\\a", 8: "\\b", 9: "\\t", 10: "\\n", 11: "\\v", 12: "\\f", 13: "\\r"}


def od_char(byte):
    return OD_ESCAPES.get(byte) or (chr(byte) if 32 <= byte < 127 else f"{byte:03o}")


OD_FORMATS = {"hex": ("-tx1", lambda b: f" {b:02x}"), "decimal": ("-tu1", lambda b: f" {b:3d}"),
              "octal": ("-to1", lambda b: f" {b:03o}"), "characters": ("-c", lambda b: f"{od_char(b):>4}")}
OD_DATA = b"Hello, World!\n\x00\x01\x02\xfe\xffend of file\n"


def od_render(intent):
    return "od" + ("" if intent.get("addresses") else " -An") + f" {OD_FORMATS[intent['format']][0]} " + quote_args([intent["source"]])


def od_fixture(intent, seed, api):
    api.binary(intent["source"], OD_DATA)


def od_check(intent, ctx):
    cell = OD_FORMATS[intent["format"]][1]
    data = ctx.binaries[abspath(intent["source"])]
    rows = [data[i:i + 16] for i in range(0, len(data), 16)]
    if any(a == b for a, b in zip(rows, rows[1:])):
        raise ValueError("od would collapse repeated rows")
    prefix = (lambda offset: f"{offset:07o}") if intent.get("addresses") else (lambda offset: "")
    lines = [prefix(index * 16) + "".join(cell(b) for b in row) for index, row in enumerate(rows)]
    return joined(lines + ([prefix(len(data))] if intent.get("addresses") else [])), "exact"


# --- split -----------------------------------------------------------------------------------------------

LETTERS = "abcdefghijklmnopqrstuvwxyz"


def split_render(intent):
    size = f" -l {intent['lines']}" if "lines" in intent else f" -b {intent['bytes']}"
    names = [intent["source"]] + ([intent["prefix"]] if "prefix" in intent else [])
    return "split" + size + (" -d" if intent.get("numeric_suffixes") else "") + " " + quote_args(names)


def split_validate(intent):
    exactly_one(intent, ("lines", "bytes"))
    if intent.get("lines", intent.get("bytes")) < 1:
        raise ValueError("size must be positive")
    if "/" in intent.get("prefix", "") or intent.get("prefix", "x").startswith("-"):
        raise ValueError("prefix must be a plain file-name prefix")


def split_fixture(intent, seed, api):
    api.file(intent["source"], "".join(f"line {i:02d} of the sample text\n" for i in range(1, 11)))


def split_check(intent, ctx):
    data = ctx.read(intent["source"]).encode()
    if "lines" in intent:
        lines = data.splitlines(keepends=True)
        chunks = [b"".join(lines[i:i + intent["lines"]]) for i in range(0, len(lines), intent["lines"])]
    else:
        chunks = [data[i:i + intent["bytes"]] for i in range(0, len(data), intent["bytes"])]
    for number, chunk in enumerate(chunks):
        suffix = f"{number:02d}" if intent.get("numeric_suffixes") else LETTERS[number // 26] + LETTERS[number % 26]
        ctx.state[abspath(intent.get("prefix", "x") + suffix)] = file_entry(chunk)
    return "", "exact"


# --- tee -------------------------------------------------------------------------------------------------


def tee_destinations(intent):
    return intent.get("destinations") or [intent["destination"]]


def tee_render(intent):
    return ("tee" + (" -a" if intent.get("append") else "") + " " + quote_args(tee_destinations(intent))
            + " < " + quote(intent["source"]))


def tee_validate(intent):
    exactly_one(intent, ("destination", "destinations"))
    if abspath(intent["source"]) in map(abspath, tee_destinations(intent)):
        raise ValueError("source and destination must differ")


def tee_fixture(intent, seed, api):
    api.file(intent["source"], "second entry\nthird entry\n")
    for name in tee_destinations(intent):
        api.file(name, "first entry\n")


def tee_check(intent, ctx):
    text = ctx.read(intent["source"])
    for name in tee_destinations(intent):
        ctx.state[abspath(name)] = file_entry((ctx.read(name) if intent.get("append") else "") + text)
    return text, "exact"


# --- xargs -----------------------------------------------------------------------------------------------

# Goals over a list of file names: delete them (rm), print them one after another (cat), create them empty
# (touch), or back each one up as a copy with a suffix (cp, one line per name, so names may contain spaces).
XARGS_EXISTING = ["old-1.log", "old-2.log", "old-3.log"]
XARGS_NEW = ["alpha.txt", "beta.txt", "gamma.txt"]
XARGS_BACKUP = ["report one.txt", "summary.txt", "budget.csv"]


def xargs_render(intent):
    if intent["command"] == "cp":
        return f"xargs -I {{}} cp {{}} {{}}{intent['suffix']} < {quote(intent['source'])}"
    return f"xargs {intent['command']} < {quote(intent['source'])}"


def xargs_validate(intent):
    if (intent["command"] == "cp") != ("suffix" in intent):
        raise ValueError("suffix is required for, and only for, backup copies")
    if "suffix" in intent and not re.fullmatch(r"[A-Za-z0-9._~-]+", intent["suffix"]):
        raise ValueError("suffix must be a plain file-name suffix")


def xargs_names(intent):
    return {"touch": XARGS_NEW, "cp": XARGS_BACKUP}.get(intent["command"], XARGS_EXISTING)


def xargs_fixture(intent, seed, api):
    names = xargs_names(intent)
    if intent["command"] != "touch":
        for name in names + ["keep.log"]:
            api.file(name, f"contents of {name}\nsecond line of {name}\n")
    api.file(intent["source"], joined(names))


def xargs_check(intent, ctx):
    text = ctx.read(intent["source"])
    if intent["command"] == "cp":
        for name in text.splitlines():
            ctx.state[abspath(name + intent["suffix"])] = file_entry(ctx.read(name))
        return "", "exact"
    names = text.split()
    if intent["command"] == "cat":
        return "".join(ctx.read(name) for name in names), "exact"
    for name in names:
        if intent["command"] == "rm":
            del ctx.state[abspath(name)]
        elif abspath(name) not in ctx.state:
            ctx.state[abspath(name)] = file_entry("")
    return "", "exact"


# --- iconv -----------------------------------------------------------------------------------------------

ICONV_TEXT = "café crème brûlée\nnaïve señor Müller\nplain ascii line\n"
PY_CODEC = {"UTF-8": "utf-8", "ISO-8859-1": "latin-1", "ASCII": "ascii", "UTF-16LE": "utf-16-le"}


def iconv_render(intent):
    output = f" -o {quote(intent['output'])}" if "output" in intent else ""
    return "iconv" + (" -c" if intent.get("discard") else "") + f" -f {intent['from']} -t {intent['to']}" + output + " " + quote_args([intent["source"]])


def iconv_validate(intent):
    if intent["from"] == intent["to"]:
        raise ValueError("from and to encodings must differ")
    if (intent["to"] == "ASCII") != bool(intent.get("discard")):
        raise ValueError("discard (iconv -c) is required for, and only for, conversion to ASCII")
    if intent["to"] in ("ISO-8859-1", "UTF-16LE") and "output" not in intent:
        raise ValueError("binary output must be written to an output file")
    if intent.get("output") == intent["source"]:
        raise ValueError("output must differ from source")


def iconv_fixture(intent, seed, api):
    if intent["from"] == "UTF-8":
        api.file(intent["source"], ICONV_TEXT)
    else:
        api.binary(intent["source"], ICONV_TEXT.encode(PY_CODEC[intent["from"]]))
    if "output" in intent and posixpath.dirname(intent["output"]):
        api.directory(posixpath.dirname(intent["output"]))


def iconv_check(intent, ctx):
    text = read_bytes(ctx, intent["source"]).decode(PY_CODEC[intent["from"]])
    converted = text.encode(PY_CODEC[intent["to"]], "ignore" if intent.get("discard") else "strict")
    if "output" in intent:
        ctx.state[abspath(intent["output"])] = file_entry(converted)
        return "", "exact"
    return converted.decode("utf-8"), "exact"


# --- base64 ----------------------------------------------------------------------------------------------

BASE64_TEXT = "username=admin\npassword=correct horse battery staple\napi_url=https://example.com/v1/\n"


def wrap_text(text, width):
    return joined(text[i:i + width] for i in range(0, len(text), width))


def base64_render(intent):
    return ("base64" + (" -d" if intent.get("decode") else "") + (f" -w {intent['wrap']}" if "wrap" in intent else "")
            + " " + quote_args([intent["source"]]))


def base64_validate(intent):
    if intent.get("decode") and "wrap" in intent:
        raise ValueError("wrap only applies to encoding")


def base64_fixture(intent, seed, api):
    if intent.get("decode"):
        api.file(intent["source"], wrap_text(base64.b64encode(BASE64_TEXT.encode()).decode(), 76))
    else:
        api.file(intent["source"], BASE64_TEXT)


def base64_check(intent, ctx):
    if intent.get("decode"):
        return base64.b64decode("".join(lines_of(ctx, intent["source"]))).decode(), "exact"
    encoded = base64.b64encode(ctx.read(intent["source"]).encode()).decode()
    if intent.get("wrap") == 0:
        return encoded, "exact"
    return wrap_text(encoded, intent.get("wrap", 76)), "exact"


# --- checksums -------------------------------------------------------------------------------------------

HASHES = {"md5sum": "md5", "sha1sum": "sha1", "sha256sum": "sha256", "sha512sum": "sha512"}


def checksum_render(intent):
    return intent["op"] + (" -c" if intent.get("check") else "") + (" -s" if intent.get("sysv") else "") + " " + quote_args(intent["sources"])


def checksum_validate(intent):
    if any("\\" in name for name in intent["sources"]):
        raise ValueError("sources must not contain backslashes")
    if intent.get("check") and len(intent["sources"]) != 1:
        raise ValueError("check reads exactly one checksum list")


def hash_text(algorithm, text):
    return hashlib.new(algorithm, text.encode()).hexdigest()


def checksum_fixture(intent, seed, api):
    if intent.get("check"):
        listing = ""
        for name in ("alpha.txt", "beta.txt"):
            content = f"contents of {name}\nsecond line\n"
            api.file(name, content)
            listing += f"{hash_text(HASHES[intent['op']], content)}  {name}\n"
        api.file(intent["sources"][0], listing)
        return
    # `sum` reports 1K blocks, so give it a file larger than one block; "empty" in a name makes an empty file.
    rows = 60 if intent["op"] == "sum" else 5
    for index, name in enumerate(intent["sources"]):
        empty = "empty" in posixpath.basename(name)
        api.file(name, "" if empty else "".join(f"record {i:03d}: the quick brown fox {index}\n" for i in range(1, rows + 1)))


def hash_check(algorithm):
    def check(intent, ctx):
        if intent.get("check"):
            out = ""
            for line in lines_of(ctx, intent["sources"][0]):
                digest, name = line.split("  ", 1)
                out += f"{name}: {'OK' if hash_text(algorithm, ctx.read(name)) == digest else 'FAILED'}\n"
            return out, "exact"
        return "".join(f"{hash_text(algorithm, ctx.read(name))}  {name}\n" for name in intent["sources"]), "exact"
    return check


def crc_table():
    table = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
        table.append(crc)
    return table


CRC_TABLE = crc_table()


def posix_cksum(data):
    """POSIX cksum: CRC-32 (poly 0x04C11DB7, MSB first) over the data then its length bytes, complemented."""
    crc = 0
    for byte in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ CRC_TABLE[((crc >> 24) ^ byte) & 0xFF]
    length = len(data)
    while length:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ CRC_TABLE[((crc >> 24) ^ length) & 0xFF]
        length >>= 8
    return ~crc & 0xFFFFFFFF


def cksum_check(intent, ctx):
    out = ""
    for name in intent["sources"]:
        data = ctx.read(name).encode()
        out += f"{posix_cksum(data)} {len(data)} {name}\n"
    return out, "exact"


def bsd_sum(data):
    """BSD checksum: 16-bit rotate-right-and-add."""
    checksum = 0
    for byte in data:
        checksum = ((checksum >> 1) + ((checksum & 1) << 15) + byte) & 0xFFFF
    return checksum


def sysv_sum(data):
    total = sum(data)
    folded = (total & 0xFFFF) + ((total & 0xFFFFFFFF) >> 16)
    return (folded & 0xFFFF) + (folded >> 16)


def sum_check(intent, ctx):
    out = ""
    for name in intent["sources"]:
        data = ctx.read(name).encode()
        if intent.get("sysv"):
            out += f"{sysv_sum(data)} {-(-len(data) // 512)} {name}\n"
        else:
            out += f"{bsd_sum(data):05d} {-(-len(data) // 1024):5d} {name}\n"
    return out, "exact"


def sources_spec(command, check, extra_fields=None):
    return Spec({"sources": "paths", **(extra_fields or {})}, frozenset({"sources"}), checksum_render, checksum_fixture, check,
                extra_validation=checksum_validate)


SPECS = {
    "sort": Spec({"source": "path", "reverse": "bool", "numeric": "bool", "unique": "bool", "key": "int", "delimiter": "text"},
                 frozenset({"source"}), sort_render, sort_fixture, sort_check, extra_validation=sort_validate),
    "awk": Spec({"source": "path", "field": "int", "delimiter": "text", "where_field": "int", "where_value": "text", "sum_field": "int"},
                frozenset({"source"}), awk_render, awk_fixture, awk_check, extra_validation=awk_validate),
    "sed": Spec({"source": "path", "pattern": "text", "replacement": "text", "global": "bool", "delete_prefix": "text",
                 "start": "int", "end": "int", "in_place": "bool"},
                frozenset({"source"}), sed_render, sed_fixture, sed_check, extra_validation=sed_validate),
    "uniq": Spec({"source": "path", "count": "bool", "duplicates": "bool", "unique": "bool"}, frozenset({"source"}),
                 uniq_render, uniq_fixture, uniq_check, extra_validation=uniq_validate),
    "cut": Spec({"source": "path", "delimiter": "text", "fields": "intlist", "characters": "text"}, frozenset({"source"}),
                cut_render, cut_fixture, cut_check, extra_validation=cut_validate),
    "tr": Spec({"source": "path", "from": "text", "to": "text", "delete": "bool", "squeeze": "bool"}, frozenset({"source", "from"}),
               tr_render, tr_fixture, tr_check, extra_validation=tr_validate),
    "paste": Spec({"sources": "paths", "delimiter": "text", "serial": "bool"}, frozenset({"sources"}),
                  paste_render, paste_fixture, paste_check, extra_validation=paste_validate),
    "nl": Spec({"source": "path", "all": "bool", "width": "int", "separator": "text", "start": "int"}, frozenset({"source"}),
               nl_render, nl_fixture, nl_check, extra_validation=nl_validate),
    "tac": multi_source_spec("tac", TAC_TEXTS, lambda lines: joined(reversed(lines))),
    "rev": multi_source_spec("rev", REV_TEXTS, lambda lines: joined(line[::-1] for line in lines)),
    "fold": Spec({"source": "path", "width": "int", "spaces": "bool"}, frozenset({"source"}),
                 fold_render, fold_fixture, fold_check, extra_validation=fold_validate),
    "expand": Spec({"source": "path", "tabstop": "int", "initial": "bool"}, frozenset({"source"}),
                   expand_render, expand_fixture, expand_check, extra_validation=expand_validate),
    "unexpand": Spec({"source": "path", "all": "bool", "tabstop": "int"}, frozenset({"source"}),
                     unexpand_render, unexpand_fixture, unexpand_check, extra_validation=unexpand_validate),
    "comm": Spec({"sources": "paths", "show": "enum:common|first_only|second_only|all"}, frozenset({"sources", "show"}),
                 comm_render, comm_fixture, comm_check, extra_validation=comm_validate),
    "od": Spec({"source": "path", "format": "enum:hex|decimal|octal|characters", "addresses": "bool"}, frozenset({"source", "format"}),
               od_render, od_fixture, od_check),
    "split": Spec({"source": "path", "lines": "int", "bytes": "int", "prefix": "text", "numeric_suffixes": "bool"}, frozenset({"source"}),
                  split_render, split_fixture, split_check, extra_validation=split_validate),
    "tee": Spec({"source": "path", "destination": "path", "destinations": "paths", "append": "bool"}, frozenset({"source"}),
                tee_render, tee_fixture, tee_check, extra_validation=tee_validate),
    "xargs": Spec({"source": "path", "command": "enum:rm|cat|touch|cp", "suffix": "text"}, frozenset({"source", "command"}),
                  xargs_render, xargs_fixture, xargs_check, extra_validation=xargs_validate),
    "iconv": Spec({"source": "path", "from": "enum:UTF-8|ISO-8859-1|UTF-16LE", "to": "enum:UTF-8|ASCII|ISO-8859-1|UTF-16LE",
                   "discard": "bool", "output": "path"},
                  frozenset({"source", "from", "to"}), iconv_render, iconv_fixture, iconv_check, extra_validation=iconv_validate),
    "base64": Spec({"source": "path", "decode": "bool", "wrap": "int"}, frozenset({"source"}),
                   base64_render, base64_fixture, base64_check, extra_validation=base64_validate),
    **{command: sources_spec(command, hash_check(algorithm), {"check": "bool"}) for command, algorithm in HASHES.items()},
    "cksum": sources_spec("cksum", cksum_check),
    "sum": sources_spec("sum", sum_check, {"sysv": "bool"}),
}
