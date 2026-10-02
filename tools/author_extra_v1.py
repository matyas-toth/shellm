"""Initial authored Extra v1 cases; committed JSONL is authoritative after creation."""

from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "eval" / "shellbench-extra-v1"
CASES = []
FAMILY = ""


def f(path):
    return {"op": "file", "path": path}


def t(op, source, **options):
    return {"op": op, "source": source, **options}


def paths(root, **options):
    return {"op": "paths", "root": root, **options}


def effect(op, **options):
    return {"op": op, **options}


def a(request, reference, out="", effects=None, cwd=".", tag="precision", mode="exact"):
    ordinal = 1 + sum(case["family"] == FAMILY for case in CASES)
    difficulty = "composition" if tag in ("composition", "pipeline", "conditional", "multi-step") else "edge" if tag in ("quoting", "literal-filenames", "regex", "symlinks", "path-interpretation") else "practical"
    CASES.append({"id": f"extra-v1-{FAMILY}-{ordinal:02d}", "family": FAMILY, "coverage": tag,
                  "difficulty": difficulty, "request": request, "reference": reference, "comparison": "number" if mode == "count" else mode,
                  "expectation": {"cwd": cwd, "stdout": out, "effects": effects or []}})


def author():
    global FAMILY
    FAMILY = "navigation"
    a("Take this shell to the very top of the filesystem, then print its resulting location.", "cd / && pwd", "/\n", cwd="/", tag="wording")
    a("Go into lab/raw/sub, step back one directory, and tell me the full path where you finish.", "cd lab/raw/sub && cd .. && pwd", "/workspace/lab/raw\n", cwd="lab/raw", tag="multi-step")
    a("I want the shell in my home folder; print the full path after switching there.", 'cd "$HOME" && pwd', "/home/shellm\n", cwd="/home/shellm", tag="wording")
    a("Hop into the folder lab/client files and show where the shell landed.", "cd 'lab/client files' && pwd", "/workspace/lab/client files\n", cwd="lab/client files", tag="quoting")
    a("Enter lab/raw and then its sibling archive using a relative path; print the ending directory.", "cd lab/raw && cd ../archive && pwd", "/workspace/lab/archive\n", cwd="lab/archive", tag="multi-step")
    a("Resolve lab/../lab/raw as the working directory and print the resulting absolute location.", "cd lab/../lab/raw && pwd", "/workspace/lab/raw\n", cwd="lab/raw", tag="path-interpretation")
    a("Change into my home directory and display welcome-extra.txt from there.", 'cd "$HOME" && cat welcome-extra.txt', f("/home/shellm/welcome-extra.txt"), cwd="/home/shellm", tag="composition")
    a("Show the absolute location of lab/client files while leaving this shell's working directory alone.", "(cd 'lab/client files' && pwd)", "/workspace/lab/client files\n", tag="composition")
    a("Follow lab/raw-shortcut as the working directory, and print the physical path instead of the link name.", "cd lab/raw-shortcut && pwd -P", "/workspace/lab/raw\n", cwd="lab/raw-shortcut", tag="symlinks")
    a("Start by entering lab/raw/sub; navigate two levels up and into work, then show the final path.", "cd lab/raw/sub && cd ../../work && pwd", "/workspace/lab/work\n", cwd="lab/work", tag="multi-step")
    a("Print the home-directory path configured for this shell, without moving the shell there.", 'printf "%s\\n" "$HOME"', "/home/shellm\n", tag="precision")
    a("From /workspace, change to the absolute directory /workspace/lab/empty vault and report that path.", "cd '/workspace/lab/empty vault' && pwd", "/workspace/lab/empty vault\n", cwd="lab/empty vault", tag="quoting")
    a("Tell me only the directory portion of lab/client files/quarter one.txt.", "dirname 'lab/client files/quarter one.txt'", {"op": "dirname", "path": "lab/client files/quarter one.txt"}, tag="path-interpretation")
    a("Extract the final filename from lab/client files/report (final).txt, keeping its extension.", "basename 'lab/client files/report (final).txt'", {"op": "basename", "path": "lab/client files/report (final).txt"}, tag="quoting")
    a("Give just the name quarter one, stripping .txt from the path lab/client files/quarter one.txt.", "basename 'lab/client files/quarter one.txt' .txt", {"op": "basename", "path": "lab/client files/quarter one.txt", "suffix": ".txt"}, tag="composition")

    FAMILY = "listing"
    a("What's immediately inside lab? One name on each line, and leave hidden entries out.", "ls -1 lab", {"op": "names", "directory": "lab"}, mode="lines", tag="wording")
    a("Show all immediate names in lab, hidden ones too, but don't include the dot and dot-dot entries.", "ls -1A lab", {"op": "names", "directory": "lab", "all": True}, mode="lines", tag="precision")
    a("Dump every immediate name from lab on separate lines, including hidden names and both dot entries.", "ls -1a lab", {"op": "names", "directory": "lab", "all": True, "dots": True}, mode="lines", tag="precision")
    a("List the immediate contents of lab/client files, preserving the filenames with spaces as individual lines.", "ls -1 'lab/client files'", {"op": "names", "directory": "lab/client files"}, mode="lines", tag="quoting")
    a("Inspect the names inside lab/raw and append a slash to directory names; one entry per line.", "ls -1p lab/raw", {"op": "names", "directory": "lab/raw", "slash": True}, mode="lines", tag="precision")
    a("List lab/archive and lab/raw themselves rather than showing what they contain.", "ls -1d lab/archive lab/raw", "lab/archive\nlab/raw\n", mode="lines", tag="precision")
    a("Show the dot-prefixed regular files directly under lab as paths, without descending into folders.", "find lab -maxdepth 1 -type f -name '.*'", paths("lab", type="f", max_depth=1, pattern=".*"), mode="lines", tag="composition")
    a("Only show immediate directory paths under lab; omit lab itself and avoid subdirectories of those folders.", "find lab -mindepth 1 -maxdepth 1 -type d", paths("lab", type="d", min_depth=1, max_depth=1), mode="lines", tag="composition")
    a("Get a separate output line for each visible .txt path directly inside lab, including its lab/ prefix.", "printf '%s\\n' lab/*.txt", paths("lab", max_depth=1, min_depth=1, pattern="*.txt", exclude=["lab/.concealed.txt"]), mode="lines", tag="composition")
    a("List the .log paths immediately in lab/logs that a normal shell glob sees, including directories ending in .log.", "printf '%s\\n' lab/logs/*.log", paths("lab/logs", max_depth=1, min_depth=1, pattern="*.log", exclude=["lab/logs/.secret.log"]), mode="lines", tag="composition")
    a("Show the hidden subtree's immediate names in lab/.private, but no dot navigation entries.", "ls -1A lab/.private", {"op": "names", "directory": "lab/.private", "all": True}, mode="lines", tag="path-interpretation")
    a("Display only the basename of each regular file immediately in lab/scan, including hidden files.", "find lab/scan -maxdepth 1 -type f -printf '%f\\n'", paths("lab/scan", type="f", max_depth=1, basename=True), mode="lines", tag="composition")
    a("Enumerate symbolic link paths anywhere below lab, without following them into their targets.", "find lab -type l", paths("lab", type="l"), mode="lines", tag="symlinks")
    a("List lab/empty vault with one entry per line and no dot entries, even though it's empty.", "ls -1 'lab/empty vault'", {"op": "names", "directory": "lab/empty vault"}, mode="lines", tag="quoting")
    a("Show the absolute paths of regular files directly within /workspace/lab/raw.", "find /workspace/lab/raw -maxdepth 1 -type f", paths("/workspace/lab/raw", max_depth=1, type="f"), mode="lines", tag="path-interpretation")

    FAMILY = "mkdir"
    a("Make a directory lab/work/release notes; those last two words are one folder name.", "mkdir 'lab/work/release notes'", effects=[effect("mkdir", paths=["lab/work/release notes"])], tag="quoting")
    a("Build the entire missing directory chain lab/work/package/assets/icons.", "mkdir -p lab/work/package/assets/icons", effects=[effect("mkdir", paths=["lab/work/package/assets/icons"], parents=True)], tag="composition")
    a("Set up lab/work/secret-box so only its owner can access it, with permissions 700.", "mkdir -m 700 lab/work/secret-box", effects=[effect("mkdir", paths=["lab/work/secret-box"], mode="700")], tag="permissions")
    a("Create both lab/work/inbox and lab/work/outbox as separate folders.", "mkdir lab/work/inbox lab/work/outbox", effects=[effect("mkdir", paths=["lab/work/inbox", "lab/work/outbox"])], tag="composition")
    a("Make the directory named -staging directly inside lab/work.", "mkdir -- lab/work/-staging", effects=[effect("mkdir", paths=["lab/work/-staging"])], tag="literal-filenames")
    a("I need a folder literally called $cache within lab/work; don't expand the dollar name.", "mkdir 'lab/work/$cache'", effects=[effect("mkdir", paths=["lab/work/$cache"])], tag="literal-filenames")
    a("Create lab/work/[queue] with the brackets retained in the directory name.", "mkdir 'lab/work/[queue]'", effects=[effect("mkdir", paths=["lab/work/[queue]"])], tag="literal-filenames")
    a("Add a directory called owner's area beneath lab/work.", 'mkdir "lab/work/owner\'s area"', effects=[effect("mkdir", paths=["lab/work/owner's area"])], tag="quoting")
    a("Make lab/work/shared-box with mode 750.", "mkdir -m 750 lab/work/shared-box", effects=[effect("mkdir", paths=["lab/work/shared-box"], mode="750")], tag="permissions")
    a("Ensure lab/raw/sub exists without failing or changing its contents when it's already there.", "mkdir -p lab/raw/sub", effects=[], tag="precision")
    a("Create lab/work/new tree/leaf along with every missing parent; the middle directory contains a space.", "mkdir -p 'lab/work/new tree/leaf'", effects=[effect("mkdir", paths=["lab/work/new tree/leaf"], parents=True)], tag="composition")
    a("Create lab/work/two; then place a nested folder named inner inside it.", "mkdir lab/work/two && mkdir lab/work/two/inner", effects=[effect("mkdir", paths=["lab/work/two", "lab/work/two/inner"])], tag="multi-step")
    a("Make lab/work/a;b as one directory, keeping the semicolon literal.", "mkdir 'lab/work/a;b'", effects=[effect("mkdir", paths=["lab/work/a;b"])], tag="literal-filenames")
    a("Create a café directory below lab/work, keeping the accented character.", "mkdir lab/work/café", effects=[effect("mkdir", paths=["lab/work/café"])], tag="quoting")
    a("Create lab/work/final and leave the shell inside it when finished.", "mkdir lab/work/final && cd lab/work/final", effects=[effect("mkdir", paths=["lab/work/final"])], cwd="lab/work/final", tag="multi-step")

    FAMILY = "touch"
    a("Put a new empty file named release notes.md into lab/work.", "touch 'lab/work/release notes.md'", effects=[effect("write", path="lab/work/release notes.md", content="")], tag="quoting")
    a("Add three zero-length files lab/work/red.tmp, lab/work/blue.tmp, and lab/work/green.tmp.", "touch lab/work/red.tmp lab/work/blue.tmp lab/work/green.tmp", effects=[effect("write", path=f"lab/work/{name}.tmp", content="") for name in ("red", "blue", "green")], tag="composition")
    a("Make an empty lab/work/-pending.txt without treating the dash as an option.", "touch -- lab/work/-pending.txt", effects=[effect("write", path="lab/work/-pending.txt", content="")], tag="literal-filenames")
    a("Create the blank file lab/work/$status.txt with a literal dollar sign.", "touch 'lab/work/$status.txt'", effects=[effect("write", path="lab/work/$status.txt", content="")], tag="literal-filenames")
    a("I need an empty file at lab/work/director's checklist.txt.", 'touch "lab/work/director\'s checklist.txt"', effects=[effect("write", path="lab/work/director's checklist.txt", content="")], tag="quoting")
    a("Create lab/work/[new]*.txt as a literal zero-byte filename, brackets and star included.", "touch 'lab/work/[new]*.txt'", effects=[effect("write", path="lab/work/[new]*.txt", content="")], tag="literal-filenames")
    a("Create a blank file called x;y.txt inside lab/work.", "touch 'lab/work/x;y.txt'", effects=[effect("write", path="lab/work/x;y.txt", content="")], tag="literal-filenames")
    a("Place a zero-byte file named café.md in lab/work.", "touch lab/work/café.md", effects=[effect("write", path="lab/work/café.md", content="")], tag="quoting")
    a("Create the missing folder lab/work/session and an empty marker file within it.", "mkdir lab/work/session && touch lab/work/session/marker", effects=[effect("mkdir", paths=["lab/work/session"]), effect("write", path="lab/work/session/marker", content="")], tag="multi-step")
    a("Create an empty file called $(printf new).txt in lab/work without evaluating its name.", "touch 'lab/work/$(printf new).txt'", effects=[effect("write", path="lab/work/$(printf new).txt", content="")], tag="literal-filenames")
    a("Make zero-length files lab/work/part 1 and lab/work/part 2, each a single filename.", "touch 'lab/work/part 1' 'lab/work/part 2'", effects=[effect("write", path=f"lab/work/part {n}", content="") for n in (1, 2)], tag="composition")
    a("Create an empty file called note (new).txt under lab/work.", "touch 'lab/work/note (new).txt'", effects=[effect("write", path="lab/work/note (new).txt", content="")], tag="literal-filenames")
    a("Set up the missing chain lab/work/run/cache and put an empty lock file at its end.", "mkdir -p lab/work/run/cache && touch lab/work/run/cache/lock", effects=[effect("mkdir", paths=["lab/work/run/cache"], parents=True), effect("write", path="lab/work/run/cache/lock", content="")], tag="multi-step")
    a("Add a blank .session file under lab/work so its name starts with a dot.", "touch lab/work/.session", effects=[effect("write", path="lab/work/.session", content="")], tag="precision")
    a("Create the empty file lab/work/ready, then print exactly ready followed by a newline.", "touch lab/work/ready && printf 'ready\\n'", "ready\n", effects=[effect("write", path="lab/work/ready", content="")], tag="multi-step")

    FAMILY = "copy"
    pairs = [("lab/client files/quarter one.txt", "lab/archive/quarter copy.txt")]
    a("Keep the original quarter one.txt in lab/client files and put a copy at lab/archive/quarter copy.txt.", "cp 'lab/client files/quarter one.txt' 'lab/archive/quarter copy.txt'", effects=[effect("copy", pairs=pairs)], tag="quoting")
    a("Back up lab/raw and its whole directory tree as the new directory lab/raw-backup.", "cp -r lab/raw lab/raw-backup", effects=[effect("copy", pairs=[["lab/raw", "lab/raw-backup"]])], tag="recursive")
    a("Copy lab/amounts.txt and lab/words.txt into the existing lab/archive directory, keeping both originals.", "cp lab/amounts.txt lab/words.txt lab/archive/", effects=[effect("copy", pairs=[[f"lab/{n}.txt", f"lab/archive/{n}.txt"] for n in ("amounts", "words")])], tag="composition")
    a("Duplicate lab/client files/director's note.txt as lab/work/memo.txt.", 'cp "lab/client files/director\'s note.txt" lab/work/memo.txt', effects=[effect("copy", pairs=[["lab/client files/director's note.txt", "lab/work/memo.txt"]])], tag="quoting")
    a("Copy the literal file lab/client files/[draft]*.txt to lab/work/literal.txt; do not expand its wildcard.", "cp 'lab/client files/[draft]*.txt' lab/work/literal.txt", effects=[effect("copy", pairs=[["lab/client files/[draft]*.txt", "lab/work/literal.txt"]])], tag="literal-filenames")
    a("Copy lab/client files/$budget.txt to lab/work/budget-copy.txt without expanding a variable.", "cp 'lab/client files/$budget.txt' lab/work/budget-copy.txt", effects=[effect("copy", pairs=[["lab/client files/$budget.txt", "lab/work/budget-copy.txt"]])], tag="literal-filenames")
    a("Place a copy of lab/client files/-receipt.txt at lab/work/receipt-copy.txt.", "cp -- 'lab/client files/-receipt.txt' lab/work/receipt-copy.txt", effects=[effect("copy", pairs=[["lab/client files/-receipt.txt", "lab/work/receipt-copy.txt"]])], tag="literal-filenames")
    a("Copy lab/client files/café.txt into lab/archive under the same basename.", "cp 'lab/client files/café.txt' lab/archive/", effects=[effect("copy", pairs=[["lab/client files/café.txt", "lab/archive/café.txt"]])], tag="quoting")
    a("Duplicate lab/client files/a;b.txt to lab/work/semicolon-copy.txt as one file.", "cp 'lab/client files/a;b.txt' lab/work/semicolon-copy.txt", effects=[effect("copy", pairs=[["lab/client files/a;b.txt", "lab/work/semicolon-copy.txt"]])], tag="literal-filenames")
    a("Copy the contents of lab/raw into the existing lab/work directory, including the nested sub directory.", "cp -r lab/raw/. lab/work/", effects=[effect("copy", pairs=[["lab/raw/readme.txt", "lab/work/readme.txt"], ["lab/raw/sub", "lab/work/sub"]])], tag="composition")
    a("First make lab/work/backup, then copy lab/prose.txt into it as prose.txt.", "mkdir lab/work/backup && cp lab/prose.txt lab/work/backup/", effects=[effect("mkdir", paths=["lab/work/backup"]), effect("copy", pairs=[["lab/prose.txt", "lab/work/backup/prose.txt"]])], tag="multi-step")
    a("Copy lab/raw/sub/chunk.txt to lab/archive/chunk-saved.txt and print the copied file.", "cp lab/raw/sub/chunk.txt lab/archive/chunk-saved.txt && cat lab/archive/chunk-saved.txt", f("lab/raw/sub/chunk.txt"), effects=[effect("copy", pairs=[["lab/raw/sub/chunk.txt", "lab/archive/chunk-saved.txt"]])], tag="multi-step")
    a("Preserve the existing link lab/raw-shortcut as a symbolic link when copying it to lab/raw-shortcut-copy.", "cp -P lab/raw-shortcut lab/raw-shortcut-copy", effects=[effect("copy", pairs=[["lab/raw-shortcut", "lab/raw-shortcut-copy"]])], tag="symlinks")
    a("Copy the two files lab/left.txt and lab/right.txt into lab/work as left.txt and right.txt.", "cp lab/left.txt lab/right.txt lab/work/", effects=[effect("copy", pairs=[[f"lab/{n}.txt", f"lab/work/{n}.txt"] for n in ("left", "right")])], tag="composition")
    a("Copy the literal filename lab/client files/$(printf oops).txt to lab/archive/kept.txt.", "cp 'lab/client files/$(printf oops).txt' lab/archive/kept.txt", effects=[effect("copy", pairs=[["lab/client files/$(printf oops).txt", "lab/archive/kept.txt"]])], tag="literal-filenames")

    FAMILY = "move"
    a("Rename lab/client files/quarter one.txt to quarter revised.txt in that same folder.", "mv 'lab/client files/quarter one.txt' 'lab/client files/quarter revised.txt'", effects=[effect("move", pairs=[["lab/client files/quarter one.txt", "lab/client files/quarter revised.txt"]])], tag="quoting")
    a("Relocate the entire lab/raw directory tree to lab/raw-renamed, leaving no lab/raw behind.", "mv lab/raw lab/raw-renamed", effects=[effect("move", pairs=[["lab/raw", "lab/raw-renamed"]])], tag="recursive")
    a("Move lab/left.txt and lab/right.txt into lab/archive while keeping their basenames.", "mv lab/left.txt lab/right.txt lab/archive/", effects=[effect("move", pairs=[[f"lab/{n}.txt", f"lab/archive/{n}.txt"] for n in ("left", "right")])], tag="composition")
    a("Move lab/client files/director's note.txt to lab/archive/director.txt, removing its old location.", 'mv "lab/client files/director\'s note.txt" lab/archive/director.txt', effects=[effect("move", pairs=[["lab/client files/director's note.txt", "lab/archive/director.txt"]])], tag="quoting")
    a("Rename the literal lab/client files/[draft]*.txt file to lab/work/draft.txt.", "mv 'lab/client files/[draft]*.txt' lab/work/draft.txt", effects=[effect("move", pairs=[["lab/client files/[draft]*.txt", "lab/work/draft.txt"]])], tag="literal-filenames")
    a("Move lab/client files/$budget.txt into lab/archive under its existing literal name.", "mv 'lab/client files/$budget.txt' lab/archive/", effects=[effect("move", pairs=[["lab/client files/$budget.txt", "lab/archive/$budget.txt"]])], tag="literal-filenames")
    a("Rename lab/client files/-receipt.txt to receipt.txt within that folder.", "mv -- 'lab/client files/-receipt.txt' 'lab/client files/receipt.txt'", effects=[effect("move", pairs=[["lab/client files/-receipt.txt", "lab/client files/receipt.txt"]])], tag="literal-filenames")
    a("Move lab/client files/café.txt to lab/work/café-saved.txt.", "mv 'lab/client files/café.txt' lab/work/café-saved.txt", effects=[effect("move", pairs=[["lab/client files/café.txt", "lab/work/café-saved.txt"]])], tag="quoting")
    a("Move lab/raw/sub/chunk.txt directly into lab, retaining only chunk.txt as its basename.", "mv lab/raw/sub/chunk.txt lab/chunk.txt", effects=[effect("move", pairs=[["lab/raw/sub/chunk.txt", "lab/chunk.txt"]])], tag="path-interpretation")
    a("Create lab/work/moved, then move lab/words.txt into that new directory.", "mkdir lab/work/moved && mv lab/words.txt lab/work/moved/", effects=[effect("mkdir", paths=["lab/work/moved"]), effect("move", pairs=[["lab/words.txt", "lab/work/moved/words.txt"]])], tag="multi-step")
    a("Move lab/prose.txt to lab/archive/prose.txt and then display it from its new location.", "mv lab/prose.txt lab/archive/prose.txt && cat lab/archive/prose.txt", f("lab/prose.txt"), effects=[effect("move", pairs=[["lab/prose.txt", "lab/archive/prose.txt"]])], tag="multi-step")
    a("Relocate the symlink lab/raw-shortcut to lab/shortcut-renamed without moving the real raw directory.", "mv lab/raw-shortcut lab/shortcut-renamed", effects=[effect("move", pairs=[["lab/raw-shortcut", "lab/shortcut-renamed"]])], tag="symlinks")
    a("Rename lab/client files/odd & ends.txt as lab/work/odds.txt, preserving its content.", "mv 'lab/client files/odd & ends.txt' lab/work/odds.txt", effects=[effect("move", pairs=[["lab/client files/odd & ends.txt", "lab/work/odds.txt"]])], tag="literal-filenames")
    a("Move lab/archive/stay.txt into lab/work under the new name archived-stay.txt; retain work/stay.txt.", "mv lab/archive/stay.txt lab/work/archived-stay.txt", effects=[effect("move", pairs=[["lab/archive/stay.txt", "lab/work/archived-stay.txt"]])], tag="precision")
    a("Move lab/client files/report (final).txt to lab/archive/final.txt as a single source file.", "mv 'lab/client files/report (final).txt' lab/archive/final.txt", effects=[effect("move", pairs=[["lab/client files/report (final).txt", "lab/archive/final.txt"]])], tag="literal-filenames")

    FAMILY = "remove"
    a("Erase only the file lab/client files/quarter one.txt, leaving the other client files alone.", "rm 'lab/client files/quarter one.txt'", effects=[effect("remove", paths=["lab/client files/quarter one.txt"])], tag="quoting")
    a("Remove the full lab/raw/sub directory tree but preserve its parent lab/raw and readme.txt.", "rm -r lab/raw/sub", effects=[effect("remove", paths=["lab/raw/sub"])], tag="precision")
    a("Delete both lab/left.txt and lab/right.txt without changing any other files.", "rm lab/left.txt lab/right.txt", effects=[effect("remove", paths=["lab/left.txt", "lab/right.txt"])], tag="composition")
    a("Delete the file whose exact path is lab/client files/director's note.txt.", 'rm "lab/client files/director\'s note.txt"', effects=[effect("remove", paths=["lab/client files/director's note.txt"])], tag="quoting")
    a("Delete lab/client files/[draft]*.txt literally; keep draftA.txt and do not expand the pattern.", "rm 'lab/client files/[draft]*.txt'", effects=[effect("remove", paths=["lab/client files/[draft]*.txt"])], tag="literal-filenames")
    a("Remove the file lab/client files/$budget.txt while keeping the dollar sign literal.", "rm 'lab/client files/$budget.txt'", effects=[effect("remove", paths=["lab/client files/$budget.txt"])], tag="literal-filenames")
    a("Delete lab/client files/-receipt.txt, interpreting the dash as part of the name.", "rm -- 'lab/client files/-receipt.txt'", effects=[effect("remove", paths=["lab/client files/-receipt.txt"])], tag="literal-filenames")
    a("Remove lab/client files/a;b.txt as one filename, not as multiple shell statements.", "rm 'lab/client files/a;b.txt'", effects=[effect("remove", paths=["lab/client files/a;b.txt"])], tag="literal-filenames")
    a("Remove just the symbolic link lab/raw-shortcut, preserving its raw directory target.", "rm lab/raw-shortcut", effects=[effect("remove", paths=["lab/raw-shortcut"])], tag="symlinks")
    a("Delete the empty directory lab/empty vault using an operation that requires it to be empty.", "rmdir 'lab/empty vault'", effects=[effect("remove", paths=["lab/empty vault"])], tag="quoting")
    selection = dict(root="lab/scan", type="f", empty=True)
    a("Delete only zero-byte regular files anywhere beneath lab/scan, preserving directories and nonempty files.", "find lab/scan -type f -empty -delete", effects=[effect("remove", selection=selection)], tag="composition")
    selection = dict(root="lab/logs", type="f", pattern="*.log", size_gt=100, exclude=["lab/logs/skip"])
    # -delete implies depth-first traversal and conflicts with pruning; use a null-safe xargs form.
    a("Remove regular .log files larger than 100 bytes below lab/logs, but never touch the skip subtree.", "find lab/logs -path lab/logs/skip -prune -o -type f -name '*.log' -size +100c -print0 | xargs -0 -r rm --", effects=[effect("remove", selection=selection)], tag="composition")
    a("Remove regular .dat files directly inside lab/scan, including hidden matches, while preserving nested files and the .dat directory.", "find lab/scan -maxdepth 1 -type f -name '*.dat' -delete", effects=[effect("remove", selection=dict(root="lab/scan", type="f", pattern="*.dat", max_depth=1))], tag="composition")
    a("Delete lab/client files/$(printf oops).txt without running the text in its filename.", "rm 'lab/client files/$(printf oops).txt'", effects=[effect("remove", paths=["lab/client files/$(printf oops).txt"])], tag="literal-filenames")
    a("Remove lab/scan/empty-directory and then print exactly removed with a newline.", "rmdir lab/scan/empty-directory && printf 'removed\\n'", "removed\n", effects=[effect("remove", paths=["lab/scan/empty-directory"])], tag="multi-step")

    FAMILY = "read"
    a("Dump the full file lab/client files/quarter one.txt to the terminal.", "cat 'lab/client files/quarter one.txt'", f("lab/client files/quarter one.txt"), tag="quoting")
    a("Read lab/client files/director's note.txt in full, including its apostrophe in the path.", 'cat "lab/client files/director\'s note.txt"', f("lab/client files/director's note.txt"), tag="quoting")
    a("Display the exact file lab/client files/[draft]*.txt, not wildcard matches.", "cat 'lab/client files/[draft]*.txt'", f("lab/client files/[draft]*.txt"), tag="literal-filenames")
    a("Show the entire contents of lab/client files/$budget.txt without substituting a variable.", "cat 'lab/client files/$budget.txt'", f("lab/client files/$budget.txt"), tag="literal-filenames")
    a("Print lab/client files/a;b.txt, keeping the semicolon inside one source path.", "cat 'lab/client files/a;b.txt'", f("lab/client files/a;b.txt"), tag="literal-filenames")
    a("Output lab/client files/-receipt.txt in full without confusing its name with a command option.", "cat -- 'lab/client files/-receipt.txt'", f("lab/client files/-receipt.txt"), tag="literal-filenames")
    a("Display the UTF-8 content of lab/client files/café.txt without modifying it.", "cat 'lab/client files/café.txt'", f("lab/client files/café.txt"), tag="quoting")
    a("Concatenate lab/right.txt followed by lab/left.txt, with no extra separators or headers.", "cat lab/right.txt lab/left.txt", {"op": "concat", "parts": [f("lab/right.txt"), f("lab/left.txt")]}, tag="composition")
    a("Read the literal file lab/client files/$(printf oops).txt without executing its name.", "cat 'lab/client files/$(printf oops).txt'", f("lab/client files/$(printf oops).txt"), tag="literal-filenames")
    a("Print my home file welcome-extra.txt using the shell's configured home path.", 'cat "$HOME/welcome-extra.txt"', f("/home/shellm/welcome-extra.txt"), tag="path-interpretation")
    a("Read lab/raw/sub/chunk.txt using the path lab/raw/sub/../sub/chunk.txt.", "cat lab/raw/sub/../sub/chunk.txt", f("lab/raw/sub/chunk.txt"), tag="path-interpretation")
    a("Read lab/raw/readme.txt through the directory symlink lab/raw-shortcut.", "cat lab/raw-shortcut/readme.txt", f("lab/raw/readme.txt"), tag="symlinks")
    a("Combine the full contents of lab/left.txt, lab/right.txt, and lab/left.txt again in precisely that order.", "cat lab/left.txt lab/right.txt lab/left.txt", {"op": "concat", "parts": [f("lab/left.txt"), f("lab/right.txt"), f("lab/left.txt")]}, tag="composition")
    a("Print lab/client files/odd & ends.txt, treating the ampersand as filename text.", "cat 'lab/client files/odd & ends.txt'", f("lab/client files/odd & ends.txt"), tag="literal-filenames")
    a("Show lab/client files/report (final).txt including every line.", "cat 'lab/client files/report (final).txt'", f("lab/client files/report (final).txt"), tag="literal-filenames")

    FAMILY = "slice"
    a("Show just the opening three lines of lab/prose.txt.", "head -n 3 lab/prose.txt", t("slice", f("lab/prose.txt"), stop=3), tag="wording")
    a("I need the bottom two lines from lab/prose.txt, in their original order.", "tail -n 2 lab/prose.txt", t("slice", f("lab/prose.txt"), start=-2), tag="wording")
    a("Display lines two through five inclusive from lab/messages.txt.", "sed -n '2,5p' lab/messages.txt", t("slice", f("lab/messages.txt"), start=1, stop=5), tag="precision")
    a("Print lab/prose.txt after skipping its first two lines.", "tail -n +3 lab/prose.txt", t("slice", f("lab/prose.txt"), start=2), tag="precision")
    a("Output lab/messages.txt with its final three lines omitted.", "head -n -3 lab/messages.txt", t("slice", f("lab/messages.txt"), stop=-3), tag="precision")
    a("Read only the first seven bytes of lab/raw/readme.txt.", "head -c 7 lab/raw/readme.txt", t("slice", f("lab/raw/readme.txt"), stop=7, bytes=True), tag="precision")
    a("Show the last five bytes in lab/raw/readme.txt, without adding your own newline.", "tail -c 5 lab/raw/readme.txt", t("slice", f("lab/raw/readme.txt"), start=-5, bytes=True), tag="precision")
    a("Print only line four of lab/messages.txt.", "sed -n '4p' lab/messages.txt", t("slice", f("lab/messages.txt"), start=3, stop=4), tag="precision")
    a("Get the last line from lab/client files/quarter one.txt.", "tail -n 1 'lab/client files/quarter one.txt'", t("slice", f("lab/client files/quarter one.txt"), start=-1), tag="quoting")
    a("Show the first line of lab/client files/director's note.txt.", 'head -n 1 "lab/client files/director\'s note.txt"', t("slice", f("lab/client files/director's note.txt"), stop=1), tag="quoting")
    a("Print the first two lines remaining after the header in lab/ledger.tsv.", "tail -n +2 lab/ledger.tsv | head -n 2", t("slice", f("lab/ledger.tsv"), start=1, stop=3), tag="pipeline")
    a("Show the last two lines of lab/messages.txt that contain literal FAIL.", "grep -F FAIL lab/messages.txt | tail -n 2", t("slice", t("filter", f("lab/messages.txt"), pattern="FAIL"), start=-2), tag="pipeline")
    a("Take lines three through six from lab/messages.txt, then print just the first two of that selection.", "sed -n '3,6p' lab/messages.txt | head -n 2", t("slice", f("lab/messages.txt"), start=2, stop=4), tag="pipeline")
    a("Print every line of lab/prose.txt except its first and last.", "sed '1d;$d' lab/prose.txt", t("slice", f("lab/prose.txt"), start=1, stop=-1), tag="precision")
    a("Sort the numbers in lab/amounts.txt numerically and display only the largest two, ascending within that pair.", "sort -n lab/amounts.txt | tail -n 2", t("slice", t("sort", f("lab/amounts.txt"), numeric=True), start=-2), tag="pipeline")

    FAMILY = "count"
    a("Give a bare count of newline characters in lab/prose.txt.", "wc -l < lab/prose.txt", t("count", f("lab/prose.txt"), unit="lines"), mode="count", tag="precision")
    a("How many whitespace-separated words occur in lab/spaced.txt? Output only the number.", "wc -w < lab/spaced.txt", t("count", f("lab/spaced.txt"), unit="words"), mode="count", tag="precision")
    a("Count the bytes, not Unicode characters, in lab/client files/café.txt.", "wc -c < 'lab/client files/café.txt'", t("count", f("lab/client files/café.txt"), unit="bytes"), mode="count", tag="quoting")
    a("Count the data rows in lab/ledger.tsv, excluding its header.", "tail -n +2 lab/ledger.tsv | wc -l", t("count", t("slice", f("lab/ledger.tsv"), start=1), unit="lines"), mode="count", tag="pipeline")
    a("Count nonblank lines in lab/prose.txt.", "grep -v '^$' lab/prose.txt | wc -l", t("count", t("filter", f("lab/prose.txt"), pattern="^$", regex=True, invert=True), unit="lines"), mode="count", tag="pipeline")
    a("Report how many lines of lab/messages.txt contain uppercase FAIL as literal text.", "grep -Fc FAIL lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="FAIL", count=True), mode="count", tag="precision")
    a("Count lines containing FAIL in lab/messages.txt without caring about case.", "grep -Fic FAIL lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="FAIL", count=True, ignore_case=True), mode="count", tag="composition")
    a("Count distinct words-as-lines in lab/words.txt; repeated lines should count once.", "sort -u lab/words.txt | wc -l", t("count", t("sort", f("lab/words.txt"), unique=True), unit="lines"), mode="count", tag="pipeline")
    a("How many regular .dat files are below lab/scan, including hidden files and nested matches? Print a number only.", "find lab/scan -type f -name '*.dat' -printf 'x\\n' | wc -l", t("count", paths("lab/scan", type="f", pattern="*.dat"), unit="lines"), mode="count", tag="composition")
    a("Count all regular files directly inside lab/client files, treating each spaced filename as one file.", "find 'lab/client files' -maxdepth 1 -type f -printf 'x\\n' | wc -l", t("count", paths("lab/client files", type="f", max_depth=1), unit="lines"), mode="count", tag="composition")
    a("Count the bytes in lab/left.txt followed by lab/right.txt as a combined stream.", "cat lab/left.txt lab/right.txt | wc -c", t("count", {"op": "concat", "parts": [f("lab/left.txt"), f("lab/right.txt")]}, unit="bytes"), mode="count", tag="pipeline")
    a("Count only the immediate subdirectories of lab, excluding lab itself and symbolic links.", "find lab -mindepth 1 -maxdepth 1 -type d -printf 'x\\n' | wc -l", t("count", paths("lab", type="d", min_depth=1, max_depth=1), unit="lines"), mode="count", tag="composition")
    a("Count empty regular files recursively under lab/scan; don't count empty directories.", "find lab/scan -type f -empty -printf 'x\\n' | wc -l", t("count", paths("lab/scan", type="f", empty=True), unit="lines"), mode="count", tag="composition")
    a("How many characters are in the exact ASCII text READY, with no newline? Print the byte count.", "printf READY | wc -c", "5\n", mode="count", tag="pipeline")
    a("Count every line obtained by concatenating lab/left.txt twice.", "cat lab/left.txt lab/left.txt | wc -l", t("count", {"op": "concat", "parts": [f("lab/left.txt"), f("lab/left.txt")]}, unit="lines"), mode="count", tag="pipeline")

    FAMILY = "grep"
    a("From lab/messages.txt, show lines containing the literal string needle.a; the dot must not match arbitrary characters.", "grep -F needle.a lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="needle.a"), tag="regex")
    a("Find the lines containing the literal text A+B in lab/messages.txt, preserving the plus sign's literal meaning.", "grep -F 'A+B' lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="A+B"), tag="regex")
    a("Extract lines containing literal [ok] from lab/messages.txt, brackets included.", "grep -F '[ok]' lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="[ok]"), tag="regex")
    a("Print lines beginning with uppercase FAIL: in lab/messages.txt.", "grep '^FAIL:' lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="^FAIL:", regex=True), tag="regex")
    a("Show either FAIL: or WARN: lines from lab/messages.txt, but only when the marker is at the beginning.", "grep -E '^(FAIL|WARN):' lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="^(FAIL|WARN):", regex=True), tag="regex")
    a("Print lab/messages.txt lines that do not contain literal [ok].", "grep -Fv '[ok]' lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="[ok]", invert=True), tag="composition")
    a("Find FAIL lines in lab/messages.txt regardless of case and prefix them with their original line numbers.", "grep -Fin FAIL lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="FAIL", ignore_case=True, numbered=True), tag="composition")
    a("Match pending as a complete word in lab/messages.txt, without matching longer words.", "grep -w pending lab/messages.txt", t("filter", f("lab/messages.txt"), pattern="pending", word=True), tag="regex")
    a("Print only the line whose entire content is first detail from lab/prose.txt.", "grep -Fx 'first detail' lab/prose.txt", t("filter", f("lab/prose.txt"), pattern="first detail", whole=True), tag="precision")
    a("Return regular file paths containing literal FIXME below lab/scan, recursively, without following symbolic links.", "find lab/scan -type f -exec grep -lF FIXME {} +", paths("lab/scan", type="f", contains="FIXME"), mode="lines", tag="composition")
    a("Show FAIL-containing lines from lab/messages.txt, numbered, then keep only the first two matches.", "grep -Fn FAIL lab/messages.txt | head -n 2", t("slice", t("filter", f("lab/messages.txt"), pattern="FAIL", numbered=True), stop=2), tag="pipeline")
    a("List regular .log file paths containing FAIL under lab/logs, excluding the entire skip directory.", "find lab/logs -path lab/logs/skip -prune -o -type f -name '*.log' -exec grep -lF FAIL {} +", paths("lab/logs", type="f", pattern="*.log", contains="FAIL", exclude=["lab/logs/skip"]), mode="lines", tag="composition")
    a("Remove blank lines and lines starting with # from the displayed output of lab/prose.txt.", "grep -Ev '^(#|$)' lab/prose.txt", t("filter", f("lab/prose.txt"), pattern="^(#|$)", regex=True, invert=True), tag="regex")
    a("Show lines ending with detail in lab/prose.txt.", "grep 'detail$' lab/prose.txt", t("filter", f("lab/prose.txt"), pattern="detail$", regex=True), tag="regex")
    a("Print lines containing a literal semicolon from the file lab/client files/a;b.txt.", "grep -F ';' 'lab/client files/a;b.txt'", t("filter", f("lab/client files/a;b.txt"), pattern=";"), tag="quoting")

    FAMILY = "find"
    a("Locate regular .dat files beneath lab/scan, recursively, treating the extension case-sensitively.", "find lab/scan -type f -name '*.dat'", paths("lab/scan", type="f", pattern="*.dat"), mode="lines", tag="precision")
    a("Find regular .dat files under lab/scan regardless of the extension's capitalization.", "find lab/scan -type f -iname '*.dat'", paths("lab/scan", type="f", pattern="*.dat", ignore_case=True), mode="lines", tag="precision")
    a("List regular .dat files in lab/scan larger than 100 bytes; match nested files too.", "find lab/scan -type f -name '*.dat' -size +100c", paths("lab/scan", type="f", pattern="*.dat", size_gt=100), mode="lines", tag="composition")
    a("Find regular .log files smaller than 100 bytes anywhere below lab/logs.", "find lab/logs -type f -name '*.log' -size -100c", paths("lab/logs", type="f", pattern="*.log", size_lt=100), mode="lines", tag="composition")
    a("List regular .log files bigger than 100 bytes under lab/logs while pruning the skip subtree.", "find lab/logs -path lab/logs/skip -prune -o -type f -name '*.log' -size +100c -print", paths("lab/logs", type="f", pattern="*.log", size_gt=100, exclude=["lab/logs/skip"]), mode="lines", tag="composition")
    a("Find only immediate regular files in lab/scan; don't descend into its child directories.", "find lab/scan -maxdepth 1 -type f", paths("lab/scan", type="f", max_depth=1), mode="lines", tag="precision")
    a("Show regular files at depth exactly two below lab/scan, excluding immediate files and anything deeper.", "find lab/scan -mindepth 2 -maxdepth 2 -type f", paths("lab/scan", type="f", min_depth=2, max_depth=2), mode="lines", tag="composition")
    a("Locate every empty directory below lab, including nested ones.", "find lab -type d -empty", paths("lab", type="d", empty=True), mode="lines", tag="precision")
    a("Find regular files whose basename is exactly quarter one.txt somewhere under lab.", "find lab -type f -name 'quarter one.txt'", paths("lab", type="f", pattern="quarter one.txt"), mode="lines", tag="quoting")
    a("Find regular .py files under lab/scan but skip everything inside vendor.", "find lab/scan -path lab/scan/vendor -prune -o -type f -name '*.py' -print", paths("lab/scan", type="f", pattern="*.py", exclude=["lab/scan/vendor"]), mode="lines", tag="composition")
    a("Find regular files ending in either .py or .txt below lab/scan.", "find lab/scan -type f \\( -name '*.py' -o -name '*.txt' \\)", paths("lab/scan", type="f", patterns=["*.py", "*.txt"]), mode="lines", tag="composition")
    a("For every regular .dat file below lab/scan, print its size in bytes, a tab, and its path; any row order is fine.", "find lab/scan -type f -name '*.dat' -printf '%s\\t%p\\n'", paths("lab/scan", type="f", pattern="*.dat", sizes=True), mode="lines", tag="composition")
    a("Print just the basenames of regular .py files beneath lab/scan, keeping repeated basenames if any.", "find lab/scan -type f -name '*.py' -printf '%f\\n'", paths("lab/scan", type="f", pattern="*.py", basename=True), mode="lines", tag="precision")
    a("Locate hidden regular files directly under lab/scan, without following symlinks or recursing.", "find lab/scan -maxdepth 1 -type f -name '.*'", paths("lab/scan", type="f", pattern=".*", max_depth=1), mode="lines", tag="composition")
    a("Find all symbolic links below lab/scan without listing the regular files they point at.", "find lab/scan -type l", paths("lab/scan", type="l"), mode="lines", tag="symlinks")

    FAMILY = "sort"
    a("Put the lines of lab/words.txt in ascending lexicographic order, retaining duplicates.", "sort lab/words.txt", t("sort", f("lab/words.txt")), tag="precision")
    a("Sort lab/amounts.txt as numbers from smallest to largest, retaining repeated values.", "sort -n lab/amounts.txt", t("sort", f("lab/amounts.txt"), numeric=True), tag="precision")
    a("Order the numbers in lab/amounts.txt largest first.", "sort -nr lab/amounts.txt", t("sort", f("lab/amounts.txt"), numeric=True, reverse=True), tag="precision")
    a("Print each distinct line of lab/words.txt once, sorted alphabetically.", "sort -u lab/words.txt", t("sort", f("lab/words.txt"), unique=True), tag="composition")
    a("Show the distinct integer values from lab/amounts.txt in increasing numeric order.", "sort -nu lab/amounts.txt", t("sort", f("lab/amounts.txt"), numeric=True, unique=True), tag="composition")
    a("Reverse the lexical sort order of lab/words.txt, still keeping repeated lines.", "sort -r lab/words.txt", t("sort", f("lab/words.txt"), reverse=True), tag="precision")
    a("Display word frequencies for lab/words.txt in alphabetical word order, using GNU uniq -c output.", "sort lab/words.txt | uniq -c", t("unique", t("sort", f("lab/words.txt")), counts=True), tag="pipeline")
    a("Output just the repeated word-lines in lab/words.txt, once per repeated value and sorted.", "sort lab/words.txt | uniq -d", t("unique", t("sort", f("lab/words.txt")), duplicates=True), tag="pipeline")
    a("Show word-lines appearing exactly once in lab/words.txt, sorted alphabetically.", "sort lab/words.txt | uniq -u", t("unique", t("sort", f("lab/words.txt")), single=True), tag="pipeline")
    a("Sort all data rows of lab/ledger.tsv by their third column numerically, omitting the header.", "tail -n +2 lab/ledger.tsv | sort -k3,3n", t("sort", t("slice", f("lab/ledger.tsv"), start=1), field=3, numeric=True), tag="pipeline")
    a("Show the three smallest entries from lab/amounts.txt after numeric sorting.", "sort -n lab/amounts.txt | head -n 3", t("slice", t("sort", f("lab/amounts.txt"), numeric=True), stop=3), tag="pipeline")
    a("Show only the largest number in lab/amounts.txt.", "sort -n lab/amounts.txt | tail -n 1", t("slice", t("sort", f("lab/amounts.txt"), numeric=True), start=-1), tag="pipeline")
    a("Sort lab/left.txt and lab/right.txt together lexicographically as one stream.", "sort lab/left.txt lab/right.txt", t("sort", {"op": "concat", "parts": [f("lab/left.txt"), f("lab/right.txt")]}), tag="composition")
    a("Remove only adjacent repeated lines from the original lab/words.txt order; don't sort first.", "uniq lab/words.txt", t("unique", f("lab/words.txt")), tag="precision")
    a("Save a numeric ascending sort of lab/amounts.txt to lab/work/sorted.txt without changing the input.", "sort -n lab/amounts.txt > lab/work/sorted.txt", effects=[effect("write", path="lab/work/sorted.txt", content=t("sort", f("lab/amounts.txt"), numeric=True))], tag="composition")

    FAMILY = "transform"
    a("Print lab/mixed.txt with ASCII letters converted to uppercase; leave the file unchanged.", "tr '[:lower:]' '[:upper:]' < lab/mixed.txt", t("translate", f("lab/mixed.txt"), upper=True), tag="precision")
    a("Display lab/mixed.txt with ASCII letters lowercased, keeping digits and spacing.", "tr '[:upper:]' '[:lower:]' < lab/mixed.txt", t("translate", f("lab/mixed.txt"), lower=True), tag="precision")
    a("Remove decimal digits from the displayed contents of lab/mixed.txt.", "tr -d '0-9' < lab/mixed.txt", t("translate", f("lab/mixed.txt"), delete="0123456789"), tag="precision")
    a("Replace runs of spaces with one space when printing lab/spaced.txt; do not collapse tabs.", "tr -s ' ' < lab/spaced.txt", t("translate", f("lab/spaced.txt"), squeeze=" "), tag="precision")
    a("Replace every tab in lab/ledger.tsv with a comma in the output.", "tr '\\t' ',' < lab/ledger.tsv", t("translate", f("lab/ledger.tsv"), **{"from": "\t", "to": ","}), tag="precision")
    a("Display lab/messages.txt with each literal FAIL replaced by ALERT, everywhere it appears.", "sed 's/FAIL/ALERT/g' lab/messages.txt", t("replace", f("lab/messages.txt"), pattern="FAIL", replacement="ALERT"), tag="precision")
    a("Print lab/prose.txt with empty lines removed.", "sed '/^$/d' lab/prose.txt", t("filter", f("lab/prose.txt"), pattern="^$", regex=True, invert=True), tag="regex")
    a("Print lab/prose.txt without lines whose first character is #.", "sed '/^#/d' lab/prose.txt", t("filter", f("lab/prose.txt"), pattern="^#", regex=True, invert=True), tag="regex")
    a("Change uppercase FAIL to ALERT inside lab/messages.txt itself, preserving the other text and files.", "sed -i 's/FAIL/ALERT/g' lab/messages.txt", effects=[effect("write", path="lab/messages.txt", content=t("replace", f("lab/messages.txt"), pattern="FAIL", replacement="ALERT"))], tag="precision")
    a("Print lab/mixed.txt with every space changed to an underscore.", "tr ' ' '_' < lab/mixed.txt", t("translate", f("lab/mixed.txt"), **{"from": " ", "to": "_"}), tag="precision")
    a("Join the lines of lab/left.txt into one comma-separated line ending in a newline.", "paste -sd ',' lab/left.txt", t("join", f("lab/left.txt"), separator=","), tag="composition")
    a("Print lab/words.txt with all lowercase vowels removed while retaining line breaks.", "tr -d aeiou < lab/words.txt", t("translate", f("lab/words.txt"), delete="aeiou"), tag="precision")
    a("Uppercase lab/words.txt, then show its unique resulting lines in alphabetical order.", "tr '[:lower:]' '[:upper:]' < lab/words.txt | sort -u", t("sort", t("translate", f("lab/words.txt"), upper=True), unique=True), tag="pipeline")
    a("Remove blank lines from lab/prose.txt and save the remaining text to lab/work/compact.txt.", "sed '/^$/d' lab/prose.txt > lab/work/compact.txt", effects=[effect("write", path="lab/work/compact.txt", content=t("filter", f("lab/prose.txt"), pattern="^$", regex=True, invert=True))], tag="composition")
    a("Print lab/messages.txt with only the text needle.a replaced by MATCH, leaving needlexa unchanged.", "sed 's/needle\\.a/MATCH/g' lab/messages.txt", t("replace", f("lab/messages.txt"), pattern=r"needle\.a", replacement="MATCH"), tag="regex")

    FAMILY = "fields"
    a("Print the second tab-separated field from every row of lab/ledger.tsv, including the header.", "cut -f2 lab/ledger.tsv", t("fields", f("lab/ledger.tsv"), delimiter="\t", columns=[2]), tag="precision")
    a("Extract columns one and three of lab/ledger.tsv, keeping a tab between them and retaining the header.", "cut -f1,3 lab/ledger.tsv", t("fields", f("lab/ledger.tsv"), delimiter="\t", columns=[1, 3]), tag="precision")
    a("Print only the city column from the simple comma-separated file lab/cities.csv, including its header.", "cut -d, -f2 lab/cities.csv", t("fields", f("lab/cities.csv"), delimiter=",", columns=[2], join=","), tag="precision")
    a("From lab/cities.csv, extract city and active columns as comma-separated text with the header.", "cut -d, -f2,3 lab/cities.csv", t("fields", f("lab/cities.csv"), delimiter=",", columns=[2, 3], join=","), tag="precision")
    a("Print the first whitespace-delimited word from each line of lab/spaced.txt, ignoring leading whitespace.", "awk '{print $1}' lab/spaced.txt", t("fields", f("lab/spaced.txt"), columns=[1], join=" "), tag="precision")
    a("Display name and score from data rows in lab/ledger.tsv, separated by one space and without the header.", "awk 'NR>1 {print $1, $3}' lab/ledger.tsv", t("fields", f("lab/ledger.tsv"), columns=[1, 3], skip_header=True, join=" "), tag="composition")
    a("Print just the names of red-team data rows in lab/ledger.tsv, omitting the header.", "awk 'NR>1 && $2==\"red\" {print $1}' lab/ledger.tsv", t("fields", f("lab/ledger.tsv"), columns=[1], skip_header=True, equals=[2, "red"], join=" "), tag="composition")
    a("List names whose numeric score is greater than ten in lab/ledger.tsv; don't print the header.", "awk 'NR>1 && $3>10 {print $1}' lab/ledger.tsv", t("fields", f("lab/ledger.tsv"), columns=[1], skip_header=True, greater=[3, 10], join=" "), tag="composition")
    a("Sum the numeric score column of lab/ledger.tsv, excluding its header, and print only the total.", "awk 'NR>1 {s+=$3} END {print s}' lab/ledger.tsv", t("fields", f("lab/ledger.tsv"), skip_header=True, sum=3), tag="composition")
    a("Print the sum of all integers in lab/amounts.txt, including repeated and negative values.", "awk '{s+=$1} END {print s}' lab/amounts.txt", t("fields", f("lab/amounts.txt"), sum=1), tag="precision")
    a("Extract data-row team names from lab/ledger.tsv and print each distinct team once in alphabetical order.", "tail -n +2 lab/ledger.tsv | cut -f2 | sort -u", t("sort", t("fields", f("lab/ledger.tsv"), delimiter="\t", columns=[2], skip_header=True), unique=True), tag="pipeline")
    a("Print city names for active=yes data rows of lab/cities.csv, without its header.", "awk -F, 'NR>1 && $3==\"yes\" {print $2}' lab/cities.csv", t("fields", f("lab/cities.csv"), delimiter=",", columns=[2], skip_header=True, equals=[3, "yes"], join=" "), tag="composition")
    a("Sum only the scores of red-team rows in lab/ledger.tsv.", "awk 'NR>1 && $2==\"red\" {s+=$3} END {print s}' lab/ledger.tsv", t("fields", f("lab/ledger.tsv"), skip_header=True, equals=[2, "red"], sum=3), tag="composition")
    a("Pair each line of lab/left.txt with the corresponding line of lab/right.txt, using a tab separator.", "paste lab/left.txt lab/right.txt", t("paste", f("lab/left.txt"), right=f("lab/right.txt")), tag="composition")
    a("Pair lab/left.txt and lab/right.txt by line, using a colon between the two values.", "paste -d: lab/left.txt lab/right.txt", t("paste", f("lab/left.txt"), right=f("lab/right.txt"), delimiter=":"), tag="composition")

    FAMILY = "write"
    a("Write exactly READY followed by one newline to the new file lab/work/status.txt, without terminal output.", "printf 'READY\\n' > lab/work/status.txt", effects=[effect("write", path="lab/work/status.txt", content="READY\n")], tag="precision")
    a("Replace lab/work/stay.txt with exactly reset and a newline.", "printf 'reset\\n' > lab/work/stay.txt", effects=[effect("write", path="lab/work/stay.txt", content="reset\n")], tag="precision")
    a("Append a line reading added to lab/work/stay.txt, keeping all existing contents.", "printf 'added\\n' >> lab/work/stay.txt", effects=[effect("write", path="lab/work/stay.txt", content={"op": "concat", "parts": [f("lab/work/stay.txt"), "added\n"]})], tag="precision")
    a("Put exactly alpha and beta on two separate lines in lab/work/two-lines.txt.", "printf 'alpha\\nbeta\\n' > lab/work/two-lines.txt", effects=[effect("write", path="lab/work/two-lines.txt", content="alpha\nbeta\n")], tag="precision")
    a("Write the literal text $HOME followed by a newline into lab/work/literal-home.txt without expanding it.", "printf '%s\\n' '$HOME' > lab/work/literal-home.txt", effects=[effect("write", path="lab/work/literal-home.txt", content="$HOME\n")], tag="literal-filenames")
    a("Save the complete lab/prose.txt stream to lab/work/prose copy.txt, leaving the source unchanged.", "cat lab/prose.txt > 'lab/work/prose copy.txt'", effects=[effect("write", path="lab/work/prose copy.txt", content=f("lab/prose.txt"))], tag="quoting")
    a("Append the complete lab/left.txt contents to the end of lab/work/stay.txt.", "cat lab/left.txt >> lab/work/stay.txt", effects=[effect("write", path="lab/work/stay.txt", content={"op": "concat", "parts": [f("lab/work/stay.txt"), f("lab/left.txt")]})], tag="composition")
    a("Write exactly 100% done and a newline to lab/work/progress.txt.", "printf '%s\\n' '100% done' > lab/work/progress.txt", effects=[effect("write", path="lab/work/progress.txt", content="100% done\n")], tag="precision")
    a("Print lab/left.txt and simultaneously save an identical copy to lab/work/left-copy.txt.", "tee lab/work/left-copy.txt < lab/left.txt", f("lab/left.txt"), effects=[effect("write", path="lab/work/left-copy.txt", content=f("lab/left.txt"))], tag="composition")
    a("Save only FAIL-containing lines from lab/messages.txt to lab/work/failures.txt, without changing the input.", "grep -F FAIL lab/messages.txt > lab/work/failures.txt", effects=[effect("write", path="lab/work/failures.txt", content=t("filter", f("lab/messages.txt"), pattern="FAIL"))], tag="composition")
    a("Write the first two lines of lab/messages.txt to lab/work/opening.txt.", "head -n 2 lab/messages.txt > lab/work/opening.txt", effects=[effect("write", path="lab/work/opening.txt", content=t("slice", f("lab/messages.txt"), stop=2))], tag="composition")
    a("Truncate lab/work/stay.txt to zero bytes while leaving the file present.", ": > lab/work/stay.txt", effects=[effect("write", path="lab/work/stay.txt", content="")], tag="precision")
    a("Save lab/right.txt followed by lab/left.txt into lab/work/combined.txt.", "cat lab/right.txt lab/left.txt > lab/work/combined.txt", effects=[effect("write", path="lab/work/combined.txt", content={"op": "concat", "parts": [f("lab/right.txt"), f("lab/left.txt")]})], tag="composition")
    a("Save the sorted unique lines from lab/words.txt into lab/work/distinct.txt.", "sort -u lab/words.txt > lab/work/distinct.txt", effects=[effect("write", path="lab/work/distinct.txt", content=t("sort", f("lab/words.txt"), unique=True))], tag="composition")
    a("Append the literal line director's ready to lab/work/stay.txt.", 'printf "%s\\n" "director\'s ready" >> lab/work/stay.txt', effects=[effect("write", path="lab/work/stay.txt", content={"op": "concat", "parts": [f("lab/work/stay.txt"), "director's ready\n"]})], tag="quoting")

    FAMILY = "permissions"
    a("Set lab/raw/readme.txt permissions to exactly 600, retaining its content.", "chmod 600 lab/raw/readme.txt", effects=[effect("chmod", paths=["lab/raw/readme.txt"], mode="600")], tag="permissions")
    a("Make lab/work accessible only to its owner by setting mode 700.", "chmod 700 lab/work", effects=[effect("chmod", paths=["lab/work"], mode="700")], tag="permissions")
    a("Give only the owner execute permission on lab/raw/readme.txt in addition to its existing read/write permissions.", "chmod u+x lab/raw/readme.txt", effects=[effect("chmod", paths=["lab/raw/readme.txt"], mode="744")], tag="permissions")
    a("Remove all permissions for other users from lab/prose.txt, leaving owner and group bits unchanged.", "chmod o-rwx lab/prose.txt", effects=[effect("chmod", paths=["lab/prose.txt"], mode="640")], tag="permissions")
    a("Set lab/client files/quarter one.txt to mode 640.", "chmod 640 'lab/client files/quarter one.txt'", effects=[effect("chmod", paths=["lab/client files/quarter one.txt"], mode="640")], tag="quoting")
    a("Set every real file and directory in lab/raw, including lab/raw itself, to mode 700 recursively.", "chmod -R 700 lab/raw", effects=[effect("chmod", paths=["lab/raw"], mode="700", recursive=True)], tag="recursive")
    a("Set both lab/left.txt and lab/right.txt to mode 600 in one command.", "chmod 600 lab/left.txt lab/right.txt", effects=[effect("chmod", paths=["lab/left.txt", "lab/right.txt"], mode="600")], tag="composition")
    a("Create lab/work/private-note as an empty file and then give it mode 600.", "touch lab/work/private-note && chmod 600 lab/work/private-note", effects=[effect("write", path="lab/work/private-note", content=""), effect("chmod", paths=["lab/work/private-note"], mode="600")], tag="multi-step")
    a("Set lab/client files/director's note.txt to mode 400 without changing its text.", 'chmod 400 "lab/client files/director\'s note.txt"', effects=[effect("chmod", paths=["lab/client files/director's note.txt"], mode="400")], tag="quoting")
    a("Print just the octal permission digits of lab/raw/readme.txt.", "stat -c '%a' lab/raw/readme.txt", "644\n", tag="permissions")
    a("Make lab/raw/sub readable, writable, and searchable only by its owner using mode 700.", "chmod 700 lab/raw/sub", effects=[effect("chmod", paths=["lab/raw/sub"], mode="700")], tag="permissions")
    a("Give group write access to lab/prose.txt while keeping its other initial permission bits.", "chmod g+w lab/prose.txt", effects=[effect("chmod", paths=["lab/prose.txt"], mode="664")], tag="permissions")
    a("Make lab/prose.txt read-only for everyone with mode 444.", "chmod 444 lab/prose.txt", effects=[effect("chmod", paths=["lab/prose.txt"], mode="444")], tag="permissions")
    a("Set lab/client files/-receipt.txt to mode 600, retaining its leading dash.", "chmod 600 -- 'lab/client files/-receipt.txt'", effects=[effect("chmod", paths=["lab/client files/-receipt.txt"], mode="600")], tag="literal-filenames")
    a("Copy lab/prose.txt to lab/work/private-copy.txt, then restrict the copy to mode 600 while keeping the source's mode unchanged.", "cp lab/prose.txt lab/work/private-copy.txt && chmod 600 lab/work/private-copy.txt", effects=[effect("copy", pairs=[["lab/prose.txt", "lab/work/private-copy.txt"]]), effect("chmod", paths=["lab/work/private-copy.txt"], mode="600")], tag="multi-step")

    FAMILY = "links"
    a("Create lab/prose-link as a symbolic link storing the relative target prose.txt.", "ln -s prose.txt lab/prose-link", effects=[effect("symlink", path="lab/prose-link", target="prose.txt")], tag="symlinks")
    a("Add a symbolic directory link lab/raw alias whose stored relative target is raw.", "ln -s raw 'lab/raw alias'", effects=[effect("symlink", path="lab/raw alias", target="raw")], tag="symlinks")
    a("Print the stored target of lab/raw-shortcut, without resolving it to an absolute path.", "readlink lab/raw-shortcut", {"op": "link_target", "path": "lab/raw-shortcut"}, tag="symlinks")
    a("Show the stored relative target of lab/scan/link.dat.", "readlink lab/scan/link.dat", {"op": "link_target", "path": "lab/scan/link.dat"}, tag="symlinks")
    a("Resolve lab/raw-shortcut to its existing absolute target path.", "readlink -f lab/raw-shortcut", "/workspace/lab/raw\n", tag="symlinks")
    a("Create lab/work/prose-ref as a symbolic link storing ../prose.txt as its target.", "ln -s ../prose.txt lab/work/prose-ref", effects=[effect("symlink", path="lab/work/prose-ref", target="../prose.txt")], tag="symlinks")
    a("Create lab/work/absolute-ref as a symlink whose stored target is /workspace/lab/prose.txt.", "ln -s /workspace/lab/prose.txt lab/work/absolute-ref", effects=[effect("symlink", path="lab/work/absolute-ref", target="/workspace/lab/prose.txt")], tag="symlinks")
    a("Replace the existing symlink lab/raw-shortcut with a symbolic link storing archive as its new target.", "ln -sfn archive lab/raw-shortcut", effects=[effect("symlink", path="lab/raw-shortcut", target="archive")], tag="symlinks")
    a("Create lab/work/-reference as a symbolic link with the stored target ../prose.txt.", "ln -s -- ../prose.txt lab/work/-reference", effects=[effect("symlink", path="lab/work/-reference", target="../prose.txt")], tag="symlinks")
    a("Create lab/work/director-ref as a symlink storing ../client files/director's note.txt as its relative target.", 'ln -s "../client files/director\'s note.txt" lab/work/director-ref', effects=[effect("symlink", path="lab/work/director-ref", target="../client files/director's note.txt")], tag="symlinks")
    a("Read the content through lab/scan/link.dat, leaving the symlink and target intact.", "cat lab/scan/link.dat", f("lab/scan/large.dat"), tag="symlinks")
    a("Remove lab/scan/link.dat alone and keep large.dat unchanged.", "unlink lab/scan/link.dat", effects=[effect("remove", paths=["lab/scan/link.dat"])], tag="symlinks")
    a("Create lab/work/future-ref as a dangling symbolic link storing nonexistent.txt; don't create the target file.", "ln -s nonexistent.txt lab/work/future-ref", effects=[effect("symlink", path="lab/work/future-ref", target="nonexistent.txt")], tag="symlinks")
    a("Create a symbolic link lab/work/words-ref to ../words.txt and then print the content through it.", "ln -s ../words.txt lab/work/words-ref && cat lab/work/words-ref", f("lab/words.txt"), effects=[effect("symlink", path="lab/work/words-ref", target="../words.txt")], tag="multi-step")
    a("Copy lab/scan/link.dat to lab/scan/link-copy.dat as a symbolic link, not as a copy of its target data.", "cp -P lab/scan/link.dat lab/scan/link-copy.dat", effects=[effect("copy", pairs=[["lab/scan/link.dat", "lab/scan/link-copy.dat"]])], tag="symlinks")

    FAMILY = "pipeline"
    a("Find uppercase FAIL lines in lab/messages.txt, alphabetically sort them, and print the result.", "grep -F FAIL lab/messages.txt | sort", t("sort", t("filter", f("lab/messages.txt"), pattern="FAIL")), tag="pipeline")
    a("Print the first two alphabetically sorted unique lines from lab/words.txt.", "sort -u lab/words.txt | head -n 2", t("slice", t("sort", f("lab/words.txt"), unique=True), stop=2), tag="pipeline")
    a("Show the three largest distinct integers in lab/amounts.txt, largest first.", "sort -nru lab/amounts.txt | head -n 3", t("slice", t("sort", f("lab/amounts.txt"), numeric=True, reverse=True, unique=True), stop=3), tag="pipeline")
    a("Get the sum of the scores belonging to blue-team rows in lab/ledger.tsv.", "awk 'NR>1 && $2==\"blue\" {s+=$3} END {print s}' lab/ledger.tsv", t("fields", f("lab/ledger.tsv"), skip_header=True, equals=[2, "blue"], sum=3), tag="composition")
    a("Sort regular .log files below lab/logs by byte size ascending and print size, a tab, and path on each line.", "find lab/logs -type f -name '*.log' -printf '%s\\t%p\\n' | sort -n", t("sort", paths("lab/logs", type="f", pattern="*.log", sizes=True), field=1, numeric=True), tag="pipeline")
    a("Count regular .py files under lab/scan while excluding all of vendor.", "find lab/scan -path lab/scan/vendor -prune -o -type f -name '*.py' -printf 'x\\n' | wc -l", t("count", paths("lab/scan", type="f", pattern="*.py", exclude=["lab/scan/vendor"]), unit="lines"), mode="count", tag="composition")
    a("Print sorted unique lowercase versions of the lines in lab/mixed.txt.", "tr '[:upper:]' '[:lower:]' < lab/mixed.txt | sort -u", t("sort", t("translate", f("lab/mixed.txt"), lower=True), unique=True), tag="pipeline")
    a("Take only nonblank, non-comment lines from lab/prose.txt and print their count.", "grep -Ev '^(#|$)' lab/prose.txt | wc -l", t("count", t("filter", f("lab/prose.txt"), pattern="^(#|$)", regex=True, invert=True), unit="lines"), mode="count", tag="pipeline")
    a("Sort the city names for active=yes rows of lab/cities.csv alphabetically, excluding the header.", "awk -F, 'NR>1 && $3==\"yes\" {print $2}' lab/cities.csv | sort", t("sort", t("fields", f("lab/cities.csv"), delimiter=",", columns=[2], skip_header=True, equals=[3, "yes"], join=" ")), tag="pipeline")
    a("Save the largest two numeric entries from lab/amounts.txt to lab/work/top-two.txt, in descending order.", "sort -nr lab/amounts.txt | head -n 2 > lab/work/top-two.txt", effects=[effect("write", path="lab/work/top-two.txt", content=t("slice", t("sort", f("lab/amounts.txt"), numeric=True, reverse=True), stop=2))], tag="pipeline")
    a("Copy the uppercase FAIL lines from lab/messages.txt to lab/work/fail-copy.txt and print that same filtered stream.", "grep -F FAIL lab/messages.txt | tee lab/work/fail-copy.txt", t("filter", f("lab/messages.txt"), pattern="FAIL"), effects=[effect("write", path="lab/work/fail-copy.txt", content=t("filter", f("lab/messages.txt"), pattern="FAIL"))], tag="pipeline")
    a("Combine lab/left.txt and lab/right.txt, sort the combined lines lexically, and save them to lab/work/merged.txt.", "cat lab/left.txt lab/right.txt | sort > lab/work/merged.txt", effects=[effect("write", path="lab/work/merged.txt", content=t("sort", {"op": "concat", "parts": [f("lab/left.txt"), f("lab/right.txt")]}))], tag="pipeline")
    a("Count uppercase FAIL lines in only the first six lines of lab/messages.txt.", "head -n 6 lab/messages.txt | grep -Fc FAIL", t("filter", t("slice", f("lab/messages.txt"), stop=6), pattern="FAIL", count=True), mode="count", tag="pipeline")
    a("Print sorted basenames of regular .dat files below lab/scan, preserving one output line per file.", "find lab/scan -type f -name '*.dat' -printf '%f\\n' | sort", t("sort", paths("lab/scan", type="f", pattern="*.dat", basename=True)), tag="pipeline")
    a("Print red-team names from lab/ledger.tsv in reverse alphabetical order without its header.", "awk 'NR>1 && $2==\"red\" {print $1}' lab/ledger.tsv | sort -r", t("sort", t("fields", f("lab/ledger.tsv"), columns=[1], skip_header=True, equals=[2, "red"], join=" "), reverse=True), tag="pipeline")

    FAMILY = "conditional"
    a("If lab/gate.ok exists, create an empty lab/work/allowed.txt; otherwise leave files untouched. Return successfully either way.", "if [ -e lab/gate.ok ]; then touch lab/work/allowed.txt; fi", effects=[effect("write", path="lab/work/allowed.txt", content="", when_exists="lab/gate.ok")], tag="conditional")
    a("Print present with a newline when lab/gate.ok exists; print absent with a newline when it doesn't.", "if [ -e lab/gate.ok ]; then printf 'present\\n'; else printf 'absent\\n'; fi", {"op": "exists_text", "path": "lab/gate.ok", "yes": "present\n", "no": "absent\n"}, tag="conditional")
    a("Ensure lab/work exists, and only after that succeeds create lab/work/complete.flag.", "mkdir -p lab/work && touch lab/work/complete.flag", effects=[effect("write", path="lab/work/complete.flag", content="")], tag="conditional")
    a("Copy lab/prose.txt to lab/work/gated-copy.txt only if lab/gate.ok exists; succeed quietly if it doesn't.", "if [ -e lab/gate.ok ]; then cp lab/prose.txt lab/work/gated-copy.txt; fi", effects=[effect("copy", pairs=[["lab/prose.txt", "lab/work/gated-copy.txt"]], when_exists="lab/gate.ok")], tag="conditional")
    a("Print directory with a newline if lab/raw is a directory, otherwise print other with a newline.", "if [ -d lab/raw ]; then printf 'directory\\n'; else printf 'other\\n'; fi", "directory\n", tag="conditional")
    a("Print linked with a newline if lab/raw-shortcut is a symbolic link; otherwise print plain with a newline.", "if [ -L lab/raw-shortcut ]; then printf 'linked\\n'; else printf 'plain\\n'; fi", "linked\n", tag="conditional")
    a("Create an empty lab/work/missing-marker.txt only if the path lab/no-such-file is absent.", "if [ ! -e lab/no-such-file ]; then touch lab/work/missing-marker.txt; fi", effects=[effect("write", path="lab/work/missing-marker.txt", content="")], tag="conditional")
    a("Print empty when lab/scan/empty.dat has zero bytes; otherwise print nonempty. End the word with a newline.", "if [ ! -s lab/scan/empty.dat ]; then printf 'empty\\n'; else printf 'nonempty\\n'; fi", "empty\n", tag="conditional")
    a("Create lab/work/guarded and, if that succeeds, write ok with a newline into its status file.", "mkdir lab/work/guarded && printf 'ok\\n' > lab/work/guarded/status", effects=[effect("mkdir", paths=["lab/work/guarded"]), effect("write", path="lab/work/guarded/status", content="ok\n")], tag="multi-step")
    a("If lab/gate.ok exists, remove it; if it doesn't, do nothing and still return success.", "if [ -e lab/gate.ok ]; then rm lab/gate.ok; fi", effects=[effect("remove", paths=["lab/gate.ok"], when_exists="lab/gate.ok")], tag="conditional")
    a("Print ready with a newline only after verifying lab/raw/readme.txt is a regular file.", "[ -f lab/raw/readme.txt ] && printf 'ready\\n'", "ready\n", tag="conditional")
    a("If lab/client files/quarter one.txt is readable, copy it to lab/work/readable-copy.txt; otherwise succeed without changing files.", "if [ -r 'lab/client files/quarter one.txt' ]; then cp 'lab/client files/quarter one.txt' lab/work/readable-copy.txt; fi", effects=[effect("copy", pairs=[["lab/client files/quarter one.txt", "lab/work/readable-copy.txt"]])], tag="conditional")
    a("Print enabled when lab/gate.ok exists and disabled otherwise, saving that newline-terminated word to lab/work/gate-state.txt.", "if [ -e lab/gate.ok ]; then printf 'enabled\\n'; else printf 'disabled\\n'; fi > lab/work/gate-state.txt", effects=[effect("write", path="lab/work/gate-state.txt", content={"op": "exists_text", "path": "lab/gate.ok", "yes": "enabled\n", "no": "disabled\n"})], tag="conditional")
    a("If lab/empty vault is a directory, remove it with rmdir; do nothing successfully if it isn't.", "if [ -d 'lab/empty vault' ]; then rmdir 'lab/empty vault'; fi", effects=[effect("remove", paths=["lab/empty vault"])], tag="conditional")
    a("Copy lab/raw/readme.txt to lab/work/verified.txt, then print the copied content only after the copy succeeds.", "cp lab/raw/readme.txt lab/work/verified.txt && cat lab/work/verified.txt", f("lab/raw/readme.txt"), effects=[effect("copy", pairs=[["lab/raw/readme.txt", "lab/work/verified.txt"]])], tag="multi-step")


def main():
    if DEST.exists():
        raise SystemExit("Extra v1 already exists; preserve it and author a new version")
    author()
    counts = Counter(case["family"] for case in CASES)
    if len(CASES) != 300 or len(counts) != 20 or set(counts.values()) != {15}:
        raise ValueError(f"Expected 20 categories of 15 cases: {counts}")
    DEST.mkdir(parents=True)
    content = "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in CASES)
    (DEST / "cases.jsonl").write_text(content, encoding="utf-8")
    manifest = {"name": "ShellBench Extra v1", "suite": "shellbench-extra-v1", "created": "2026-10-02",
                "role": "long-term progress benchmark; separate from training and loss validation",
                "cases": len(CASES), "families": dict(counts),
                "coverage": dict(Counter(case["coverage"] for case in CASES)),
                "difficulty": dict(Counter(case["difficulty"] for case in CASES)),
                "cases_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "authoring": "300 authored request/reference/expectation triples; no training catalog imports"}
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
