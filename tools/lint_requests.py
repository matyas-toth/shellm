"""Lint catalog requests for quality problems the compiler cannot see.

Errors (exit status 1):
- a request names a program (it should describe the goal, not dictate the tool),
- the same request skeleton maps to commands of different families (conflicting labels),
- a validation request reuses a sentence template seen in that family's training scenarios,
- a scenario's paraphrases differ only by their first word.

Usage: python tools/lint_requests.py [--release pilot-v1] [--all] [--family NAME ...]
By default the original pilot families (authored before this lint) are skipped.
"""

import argparse
from collections import defaultdict
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shellm_data.core import source_groups  # noqa: E402
from shellm_data.intents import render  # noqa: E402

LEGACY = {"pwd", "cd", "ls", "mkdir", "touch", "cp", "mv", "rm", "cat", "head", "tail", "wc", "grep", "find"}

# Program names that are not ordinary English words in a request. English verbs that are also commands
# (sort, cut, paste, split, test, sleep, install, shred, truncate, find, ...) are allowed.
PROGRAMS = {"printf", "printenv", "env", "stat", "du", "expr", "dd", "unlink", "gunzip", "zcat", "md5sum", "sha1sum",
            "sha256sum", "sha512sum", "cksum", "nl", "od", "tac", "rev", "awk", "sed", "tr", "uniq", "xargs", "iconv",
            "mkfifo", "readlink", "realpath", "basename", "dirname", "fallocate", "seq", "whoami", "chmod", "mkdir", "ls",
            "rm", "cp", "mv", "pwd", "wc", "grep", "comm", "unexpand"}
# Format or algorithm names a user naturally mentions.
FORMATS = {"gzip", "base64"}
# Families that wrap another command; the wrapped program may be named in the request.
WRAPPERS = {"env", "timeout", "xargs"}
TOOL_PHRASE = re.compile(r"\b(?:using|with|via|use|run|execute|invoke|call)\s+(?:the\s+)?([a-z0-9]+)\b"
                         r"|\bthe\s+([a-z0-9]+)\s+(?:command|program|utility|tool)\b")


def literals(value):
    if isinstance(value, bool):
        return []
    if isinstance(value, (str, int)):
        return [str(value)]
    if isinstance(value, list):
        return [x for v in value for x in literals(v)]
    if isinstance(value, dict):
        return [x for v in value.values() for x in literals(v)]
    return []


def skeleton(request, intent):
    text = request.lower()
    for value in sorted({v for v in literals({k: v for k, v in intent.items() if k != "op"}) if v}, key=len, reverse=True):
        text = re.sub(r"(?<![\w])" + re.escape(value.lower()) + r"(?![\w])", "<a>", text)
    return re.sub(r"(?<![\w-])\d+(?![\w-])", "<n>", text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", default="pilot-v1")
    parser.add_argument("--all", action="store_true", help="also lint the original pilot families")
    parser.add_argument("--family", action="append", help="only report these families")
    args = parser.parse_args()

    groups = source_groups(args.release)
    skeleton_owner = {group["family"] for group in groups}
    selected =lambda family: (args.all or family not in LEGACY) and (not args.family or family in args.family)
    errors = []
    skeleton_families = defaultdict(set)
    train_skeletons = defaultdict(set)
    for group in groups:
        for request in group["requests"]:
            skeleton_families[skeleton(request, group["intent"])].add(group["family"])
            if group["split"] == "train":
                train_skeletons[group["family"]].add(skeleton(request, group["intent"]))

    for group in groups:
        family, gid = group["family"], group["id"]
        if not selected(family):
            continue
        command = render(group["intent"])
        wrapped = set(re.findall(r"[a-z0-9]+", command)) & (PROGRAMS | set(skeleton_owner))
        allowed = FORMATS | ((wrapped - {family}) if family in WRAPPERS else set())
        for request in group["requests"]:
            masked = skeleton(request, group["intent"])  # file names and other arguments are masked out
            words = set(re.findall(r"[a-z0-9]+", masked))
            phrases = {m for pair in TOOL_PHRASE.findall(masked) for m in pair if m}
            named = (words & PROGRAMS) | (phrases & (PROGRAMS | {family}))
            named -= allowed
            if named:
                errors.append(f"{gid}: names a program {sorted(named)}: {request}")
            shape = skeleton(request, group["intent"])
            if len(skeleton_families[shape]) > 1:
                errors.append(f"{gid}: same request skeleton used by {sorted(skeleton_families[shape])}: {request}")
            if group["split"] == "validation" and shape in train_skeletons[family]:
                errors.append(f"{gid}: validation reuses a training sentence template: {request}")
        tails = {request.split(" ", 1)[-1] for request in group["requests"]}
        if len(group["requests"]) > 1 and len(tails) == 1:
            errors.append(f"{gid}: paraphrases differ only by their first word")

    for error in errors:
        print(error)
    print(f"{len(errors)} problem(s) in {sum(selected(g['family']) for g in groups)} linted groups")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
