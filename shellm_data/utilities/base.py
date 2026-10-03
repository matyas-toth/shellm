"""Shared contract for table-driven command families (text, files, shell utilities)."""

from dataclasses import dataclass
import posixpath
import re
import shlex
from typing import Callable, Optional

BAD = "\n\r\0"


def abspath(value):
    if value == "~":
        return "/home/shellm"
    return posixpath.normpath(value if value.startswith("/") else "/workspace/" + value)


SAFE_WORD = re.compile(r"[A-Za-z0-9_@%+=:,./-]+")


def quote(value):
    """Quote the way a person would (and as both evaluation suites do): bare when safe, single quotes
    otherwise, and double quotes around a value containing an apostrophe but nothing double quotes expand."""
    if SAFE_WORD.fullmatch(value):
        return value
    if "'" not in value:
        return "'" + value + "'"
    if not re.search(r'["$`\\!]', value):
        return '"' + value + '"'
    return shlex.quote(value)


def quote_args(values):
    """Quote values for a command line, guarding leading dashes with `--`."""
    return ("-- " if any(v.startswith("-") for v in values) else "") + " ".join(quote(v) for v in values)


def _text(value):
    return isinstance(value, str) and bool(value) and not any(c in value for c in BAD)


def check_kind(name, kind, value):
    if kind in ("text", "path"):
        ok = _text(value)
    elif kind == "paths":
        ok = isinstance(value, list) and bool(value) and len(set(value)) == len(value) and all(_text(v) for v in value)
    elif kind == "int":
        ok = type(value) is int and value >= 0
    elif kind == "intlist":
        ok = isinstance(value, list) and bool(value) and all(type(v) is int and v >= 1 for v in value)
    elif kind == "bool":
        ok = type(value) is bool
    elif kind.startswith("enum:"):
        ok = value in kind[5:].split("|")
    else:
        raise ValueError(f"Unknown field kind {kind}")
    if not ok:
        raise ValueError(f"Invalid {name}: {value!r}")


@dataclass
class Spec:
    """One command family.

    fields: field name -> kind ("text", "path", "paths", "int", "intlist", "bool", "enum:a|b|c").
    required: names that must be present (all other fields are optional).
    render(intent) -> the canonical Bash command string.
    fixture(intent, seed, api): create the files the command needs. api offers
        api.file(name, text=None), api.directory(name), api.binary(name, data: bytes),
        api.symlink(name, target) (target as it would be given to ln -s, relative to the link's directory), api.seed.
    check(intent, ctx) -> (expected_stdout, mode): independently compute the expected effect
        WITHOUT running the command. Mutate ctx.state in place for filesystem changes. mode is one
        of "exact", "lines", "count", "number", "listing". ctx offers ctx.read(name) -> text of a
        fixture file, ctx.files {abs path: text}, ctx.binaries {abs path: bytes}, ctx.state,
        ctx.outcome, ctx.spec.
    returncode: expected exit status of the reference command (default 0).
    extra_validation(intent): optional cross-field rules; raise ValueError.
    """

    fields: dict
    required: frozenset
    render: Callable
    fixture: Callable
    check: Callable
    returncode: int = 0
    extra_validation: Optional[Callable] = None

    @property
    def optional(self):
        return set(self.fields) - set(self.required)

    def validate(self, intent):
        for name, value in intent.items():
            if name != "op":
                check_kind(name, self.fields[name], value)
        if self.extra_validation:
            self.extra_validation(intent)
