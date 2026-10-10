"""Author pilot-v2 from an explicit semantic matrix, never from benchmark requests.

Only writes editable catalogs and authoring metadata. Compile with shellm_data
after reviewing them. Existing rendered releases are never overwritten.
"""

from collections import Counter, defaultdict
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shellm_data.core import DATA, compile_examples, digest, source_groups, check_records
from shellm_data.intents import render

RELEASE = "pilot-v2"
PREFIX = "coverage-v2-"
# These vocabulary pools are disjoint by construction, rather than a row shuffle.
TRAIN_NAMES = "cinder kiln ledger harbor prism orchard canvas spool beacon lantern quartz meadow parcel cobalt atlas rivet gasket spindle vault basket ember pollen turbine compass willowbrook satchel mosaic relay vector loam quarry ribbon cassette loom terrace depot estuary thimble pigment junction".split()
VALIDATION_NAMES = "verdigris mariner vellum coracle fulcrum tundralake obsidian meridian palisade almanac".split()

# Each pair is six authored training forms and six separate validation forms.
# Slots insert literal arguments or explicit constraints, not benchmark sentences.
PHRASES = {
    "cd": (
        ["Take my terminal into {place}.", "I want this shell to work from {place}.",
         "Make {place} the active working directory.", "Switch the terminal's location to {place}.",
         "Can I start working inside {place}?", "Go to {place} in this shell session."],
        ["Set the session's working location to {place}.", "From now on, operate in {place}.",
         "Move the shell's current location into {place}.", "Use {place} as my current directory.",
         "The terminal should be positioned at {place}.", "Change where this session is working: {place}."]),
    "ls": (
        ["What's immediately inside {place}? Show {items}{style}.", "List {items} directly in {place}{style}.",
         "Give me {items} from {place}{style}; don't descend into child folders.",
         "I'd like to see {items} immediately under {place}{style}.",
         "Display the contents of {place}{style}, showing {items}.",
         "Show a directory listing for {place}: {items}{style}."],
        ["For {place}, report {items}{style} at the top level only.",
         "Let me inspect {items} directly inside {place}{style}.",
         "Return {items}{style} from the immediate contents of {place}.",
         "Present a listing of {place}{style}, limited to {items}.",
         "I need the immediate entries of {place}: {items}{style}.",
         "Reveal {items} in {place}{style}, without walking the tree."]),
    "mkdir": (
        ["Create {targets}{condition}.", "I need {targets} created{condition}.",
         "Make {targets}{condition} so I can store things there.",
         "Set up {targets}{condition}.", "Could you create {targets}{condition}?",
         "Add {targets} to the filesystem{condition}."],
        ["Provision {targets}{condition}.", "Establish {targets}{condition} for me.",
         "I'd like {targets} to exist{condition}.", "Prepare {targets}{condition}.",
         "Give me {targets}{condition}.", "Arrange for {targets} to be created{condition}."]),
    "touch": (
        ["Create {targets}; they don't exist yet.", "I need {targets} with no contents yet.",
         "Make {targets}, leaving them empty.", "Add {targets} as empty placeholders.",
         "Can you create {targets} without writing any text?", "Start with {targets} containing zero bytes."],
        ["Put {targets} on disk as empty new files.", "Initialize {targets} with no data in them.",
         "Set up {targets} as zero-length files.", "I'd like blank placeholders at {targets}.",
         "Produce {targets}, but leave their contents blank.", "Prepare {targets} as new empty files."]),
    "touch-in-dir": (
        ["Create an empty file called {filename} inside the existing folder {directory}.",
         "Put a new blank file named {filename} in {directory}.",
         "I need an empty {filename} file under {directory}.",
         "Inside {directory}, create a file named {filename} with no contents.",
         "Make a zero-byte file named {filename} in the directory {directory}.",
         "Add an empty placeholder named {filename} to {directory}."],
        ["Initialize a blank file called {filename} within {directory}.",
         "Under the folder {directory}, set up the empty file {filename}.",
         "Give me a new zero-length {filename} file inside {directory}.",
         "The existing directory {directory} needs a new empty file called {filename}.",
         "Place a blank placeholder named {filename} within {directory}.",
         "Prepare {filename} as an empty new file in the folder {directory}."]),
    "cp": (
        ["Duplicate {subject} {target}, keeping the original.", "Copy {subject} {target}.",
         "Keep {subject} where it is and put a copy {target}.",
         "I need another copy of {subject} {target}.", "Make a duplicate of {subject} {target}.",
         "Can you copy {subject} {target} without moving it?"],
        ["Place a duplicate of {subject} {target} and preserve the source.",
         "Replicate {subject} {target}.", "Leave the original intact while copying {subject} {target}.",
         "Reproduce {subject} {target} without deleting the source.",
         "Create a second copy of {subject} {target}.", "Save a copy of {subject} {target}; retain the original."]),
    "mv": (
        ["Move {subject} {target}.", "Relocate {subject} {target}; don't keep a copy at the old location.",
         "Transfer {subject} {target}, removing the source location.",
         "I want {subject} moved {target}.", "Put {subject} {target} instead of where it is now.",
         "Can you move {subject} {target} without leaving the original behind?"],
        ["Shift {subject} {target} and remove the old entry.", "Change the location of {subject} {target}.",
         "Rehome {subject} {target}, leaving no copy at the source.",
         "Relocate {subject} {target}; leave nothing at its former location.",
         "Carry {subject} {target} rather than copying it.", "Take {subject} {target} and discard its former location."]),
    "rm": (
        ["Delete {subject}.", "Remove {subject} from disk.", "I don't need {subject}; erase it.",
         "Get rid of {subject}.", "Can you delete {subject} for me?", "Erase {subject} completely."],
        ["Discard {subject} from the filesystem.", "Please remove {subject} permanently.",
         "Clear out {subject}.", "I want {subject} gone from disk.",
         "Wipe away {subject}.", "Delete the filesystem entries for {subject}."]),
    "cat-read": (
        ["Print {sources} in full, in that order.", "Show the complete contents of {sources} in order.",
         "Display all the text from {sources}, one after the other.",
         "Read {sources} to the terminal without modifying them, in the listed order.",
         "I want all of {sources} printed in order.", "Output {sources} completely, following their stated order."],
        ["Emit the entire contents of {sources} sequentially.", "Let me read all of {sources} in the order given.",
         "Write {sources} to standard output in order, leaving the files unchanged.",
         "Return every byte of {sources}, concatenated in the specified order.",
         "Present the whole text of {sources} in sequence.", "Send the contents of {sources} to my terminal in order."]),
    "cat-write": (
        ["Combine {sources}, in that order, into {output}; replace its existing contents.",
         "Write all of {sources} in sequence to {output}, overwriting that file.",
         "I need {output} replaced by the concatenation of {sources} in the stated order.",
         "Join {sources} in order and save the result in {output}, replacing old data.",
         "Copy the contents of {sources} sequentially into {output}; overwrite the destination.",
         "Create the combined text of {sources} in {output}, in order, discarding its previous contents."],
        ["Replace the data in {output} with all of {sources}, concatenated in order.",
         "Save {sources} sequentially as the new contents of {output}.",
         "Overwrite {output} with the joined contents of {sources}, in the given order.",
         "Put the concatenation of {sources} into {output}; replace the destination's text.",
         "Rebuild {output} from the full contents of {sources} in sequence.",
         "Store {sources}, joined in order, in {output} instead of its old contents."]),
    "cat-append": (
        ["Append {sources}, in that order, to {output}; keep its existing text.",
         "Add the contents of {sources} to the end of {output}, in sequence.",
         "Extend {output} with all of {sources} in order without overwriting it.",
         "Keep the current text in {output} and append {sources} in the listed order.",
         "I need {sources} joined onto the end of {output}, in that order.",
         "Append all the text of {sources} sequentially after the existing contents of {output}."],
        ["Preserve {output}'s text, then add {sources} at its end in order.",
         "Grow {output} by appending the full contents of {sources} sequentially.",
         "Write {sources} after the last byte of {output}, following the given order.",
         "Attach the text of {sources} in sequence to the existing contents of {output}.",
         "Leave {output}'s old data intact and append {sources} in order.",
         "Add {sources} sequentially after everything already in {output}."]),
    "head": (
        ["Show the first {count} {unit} of {source}.", "Print {count} {unit} from the start of {source}.",
         "I only want the opening {count} {unit} from {source}.",
         "Display {source} up to its first {count} {unit}.",
         "Read the beginning of {source}, limited to {count} {unit}.",
         "Give me {count} {unit} from the beginning of {source}."],
        ["Return the initial {count} {unit} of {source}.", "Take {count} {unit} off the front of {source} and print them.",
         "Present just the leading {count} {unit} from {source}.",
         "Emit a {count}-{unit} prefix of {source}.", "Output only the first {count} {unit} from {source}.",
         "Let me inspect the beginning of {source}: {count} {unit}." ]),
    "tail": (
        ["Show the last {count} {unit} of {source}.", "Print {count} {unit} from the end of {source}.",
         "I only want the final {count} {unit} from {source}.",
         "Display the end of {source}, limited to {count} {unit}.",
         "Read the closing {count} {unit} of {source}.",
         "Give me {count} {unit} from the bottom of {source}."],
        ["Return the terminal {count} {unit} of {source}.", "Take {count} {unit} off the back of {source} and print them.",
         "Present just the trailing {count} {unit} from {source}.",
         "Emit a {count}-{unit} suffix of {source}.", "Output only the last {count} {unit} from {source}.",
         "Let me inspect the ending of {source}: {count} {unit}." ]),
    "wc": (
        ["Count the {unit} in {source}.", "How many {unit} does {source} contain?",
         "Give me the number of {unit} in {source}.", "Measure {source} by its total {unit}.",
         "I need a count of {unit} for {source}.", "Report the total number of {unit} in {source}."],
        ["What's the {unit} count for {source}?", "Calculate how many {unit} are in {source}.",
         "Tell me {source}'s total {unit}.", "Determine the number of {unit} contained in {source}.",
         "Return a tally of {unit} from {source}.", "Get the total {unit} in {source}." ]),
    "grep": (
        ["In {source}, {action} {selection}{case}.", "{action_cap} {selection} from {source}{case}.",
         "I need you to {action} {selection} in {source}{case}.",
         "For {source}, {action} only {selection}{case}.",
         "Could you {action} {selection} from {source}{case}?",
         "Read {source} and {action} {selection}{case}."],
        ["Looking through {source}, {action} {selection}{case}.",
         "From the text in {source}, {action} {selection}{case}.",
         "Please {action} {selection}{case}, using {source} as input.",
         "Examine {source} to {action} {selection}{case}.",
         "For my input file {source}, I want to {action} {selection}{case}.",
         "Go through {source}; {action} {selection}{case}." ]),
    "grep-files": (
        ["Search {source} recursively for literal text {pattern}; return matching filenames only{case}.",
         "Which files anywhere under {source} contain the literal text {pattern}{case}? Print their paths only.",
         "List paths of files containing literal {pattern} throughout {source} and its subdirectories{case}.",
         "I need filenames, not matching lines, for literal {pattern} anywhere in {source}{case}.",
         "Find files by their contents: literal {pattern}, recursively in {source}{case}. Output paths only.",
         "Look inside every file below {source} for literal {pattern} and show matching file paths{case}."],
        ["Return only file paths from a recursive content search for literal {pattern} in {source}{case}.",
         "Walk all of {source} and list the files whose text contains literal {pattern}{case}.",
         "Check file contents below {source} for literal {pattern}{case}; report matching paths.",
         "Give me filenames containing literal {pattern} in the entire {source} tree{case}.",
         "Locate literal {pattern} inside files under {source}{case}, including nested files; print only filenames.",
         "Inspect {source} recursively and name files containing literal {pattern}{case}." ]),
    "find": (
        ["Find {selection} {scope}.", "List paths for {selection} {scope}.",
         "I need the paths of {selection} {scope}.", "Locate {selection} {scope} and print their paths.",
         "Which entries are {selection} {scope}? Show their paths.",
         "Search for {selection} {scope}; output paths only."],
        ["Return pathnames for {selection} {scope}.", "Identify {selection} {scope} by pathname.",
         "Collect the paths of {selection} {scope}.", "Enumerate {selection} {scope}, showing each path.",
         "I want a path list of {selection} {scope}.", "Report where {selection} are {scope}." ]),
    "chmod": (
        ["Set the permissions of {targets} to {mode}{scope}.",
         "Give {targets} octal permissions {mode}{scope}.",
         "I need {targets} to have mode {mode}{scope}.",
         "Change the access mode on {targets} to {mode}{scope}.",
         "Apply permission bits {mode} to {targets}{scope}.",
         "Make the mode of {targets} exactly {mode}{scope}."],
        ["Assign octal mode {mode} to {targets}{scope}.",
         "Use permission value {mode} for {targets}{scope}.",
         "The access bits for {targets} should be {mode}{scope}.",
         "Update {targets} so their permissions are {mode}{scope}.",
         "Replace the permission bits on {targets} with {mode}{scope}.",
         "Configure {targets} with octal permissions {mode}{scope}." ]),
}


def named(value):
    return f'"{value}"'


def listed(values):
    return " and ".join(named(v) for v in values)


def context(name, index):
    """Literal shell hazards occur across operations, never as executable content."""
    shapes = [name + "-journal", name + " working notes", name + "'s notebook",
              "-" + name + "-draft", name + "-$budget", name + ";archive",
              name + "*literal", name + "[draft]", name + "-café", name + " field records"]
    return shapes[index % len(shapes)]


def author():
    inherited = source_groups("pilot-v1")
    groups = [{k: v for k, v in g.items() if k != "source"} for g in inherited]
    seen = {digest(g["intent"]): g["split"] for g in inherited}
    used_requests = {r.lower() for g in inherited for r in g["requests"]}
    counts = Counter()

    def add(intent, capability, key, split, **slots):
        render(intent)  # Reject malformed intents before authoring English.
        # Identical semantic scenarios stay in one split. The release audit also
        # checks rendered labels, including dictionaries that render alike.
        marker = digest(intent)
        if marker in seen:
            if seen[marker] != split:
                raise ValueError(f"Intent reused across splits: {intent}")
            return
        requests = [form.format(**slots) for form in PHRASES[key][split == "validation"]]
        if any(r.lower() in used_requests for r in requests):
            raise ValueError(f"Repeated authored request: {requests}")
        used_requests.update(r.lower() for r in requests)
        seen[marker] = split
        op = intent["op"]
        counts[op] += 1
        topic = "navigation" if op in ("cd", "pwd") else "search" if op == "find" else "text" if op in ("cat", "head", "tail", "wc", "grep") else "filesystem"
        groups.append({"id": f"{PREFIX}{op}-{counts[op]:04d}", "family": op, "topic": topic,
                       "capability": capability, "split": split, "intent": intent, "requests": requests})

    for index, name in enumerate(TRAIN_NAMES + VALIDATION_NAMES):
        split = "train" if index < len(TRAIN_NAMES) else "validation"
        base = context(name, index)
        src = base + ".txt"
        other = base + "-second.txt"
        out = base + "-joined.txt"
        tree = ("./" if base.startswith("-") else "") + base + "-tree"
        for dest in (base, "./" + base, "../workspace/" + base, "/workspace/" + base):
            qualifier = "the absolute directory path " if dest.startswith("/") else "the parent-relative directory path " if dest.startswith("../") else "the dot-relative directory path " if dest.startswith("./") else "the relative directory path "
            add({"op": "cd", "destination": dest}, "path-resolution", "cd", split, place=qualifier + named(dest))

        # Short forms like "here" denote '.', never a literal folder named here.
        for directory in (base,):
            place = "the directory " + named(directory)
            for all_entries, long, one in ((False, False, False), (True, False, False),
                                            (False, True, False), (True, True, False),
                                            (False, False, True), (True, False, True)):
                intent = {"op": "ls", "directory": directory, "all": all_entries, "long": long, "one": one}
                items = "all entries, including hidden ones" if all_entries else "non-hidden entries"
                style = " with permissions, ownership and sizes" if long else " with exactly one entry per line" if one else ""
                add(intent, "listing-options", "ls", split, place=place, items=items, style=style)

        for kind in range(5):
            targets = [base + "-folder"] if kind == 0 else [base + "-one", base + "-two"] if kind == 1 else [base + "/stage/final"] if kind in (2, 4) else [base + "-private"]
            intent = {"op": "mkdir", "targets": targets}
            if kind in (2, 4):
                intent["parents"] = True
            if kind in (3, 4):
                intent["mode"] = "700" if kind == 3 else "750"
            condition = ", creating any missing parent directories" if intent.get("parents") else ""
            if "mode" in intent:
                condition += f", with the final directory's permissions set to {intent['mode']}"
            add(intent, "directory-creation-composition" if kind == 4 else "directory-creation", "mkdir", split,
                targets=("directories named " if len(targets) > 1 else "a directory named ") + listed(targets), condition=condition)

        for targets in ([src], [src, other]):
            add({"op": "touch", "targets": targets}, "literal-empty-files", "touch", split,
                targets=("files named " if len(targets) > 1 else "a file named ") + listed(targets))
        add({"op": "touch", "targets": [tree + "/" + src]}, "filename-directory-composition", "touch-in-dir", split,
            filename=named(src), directory=named(tree))
        for op in ("cp", "mv"):
            for kind in range(4):
                intent = {"op": op, "sources": [src], "destination": out}
                subject = "the file " + named(src)
                target = "to the file path " + named(out)
                if kind in (1, 2):
                    intent.update(into=True, destination=tree)
                    target = "into the existing directory " + named(tree)
                    if kind == 2:
                        intent["sources"].append(other)
                        subject = "the files " + listed(intent["sources"])
                elif kind == 3:
                    intent.update(sources=[tree], destination=base + "-tree-saved", directory_source=True)
                    subject = "the directory " + named(tree) + " with all its nested contents"
                    target = "to the new directory path " + named(intent["destination"])
                add(intent, "copy-move-destination" if kind != 3 else "recursive-directory-transfer", op, split, subject=subject, target=target)

        for recursive in (False, True):
            targets = [tree] if recursive else [src, other]
            add({"op": "rm", "targets": targets, "recursive": recursive}, "explicit-removal", "rm", split,
                subject=("the directory " + named(tree) + " and everything underneath it") if recursive else "the files " + listed(targets))

        for kind in range(4):
            sources = [src] if kind == 0 else [src, other]
            intent = {"op": "cat", "sources": sources}
            key = "cat-read"
            if kind > 1:
                intent["output"] = out
                key = "cat-write"
            if kind == 3:
                intent["append"] = True
                key = "cat-append"
            add(intent, "read-overwrite-append" if kind > 1 else "ordered-file-reading", key, split, sources=listed(sources), output=named(out))

        for op in ("head", "tail"):
            for count, byte_mode in ((1, False), (3 + index % 9, False), (7 + index % 13, True), (31 + index % 7, True)):
                add({"op": op, "source": src, "count": count, "bytes": byte_mode}, "start-end-lines-bytes", op, split,
                    count=count, unit="bytes" if byte_mode else "line" if count == 1 else "lines", source=named(src))
        for unit in ("lines", "words", "bytes"):
            add({"op": "wc", "source": src, "unit": unit}, "count-units", "wc", split, unit=unit, source=named(src))

        pattern = ["NOTICE.", "FAIL+", "FLAG[", "$PRICE", "-EVENT", "STATE:", "WARN*", "Step(", "CODE?", "CHECK]"][index % 10] + name
        for kind in range(9):
            intent = {"op": "grep", "pattern": pattern, "source": src}
            if kind in (1, 4, 6, 8):
                intent["ignore_case"] = True
            if kind in (2, 6):
                intent["invert"] = True
            if kind in (3, 4):
                intent["line_numbers"] = True
            if kind in (5, 6):
                intent["count"] = True
            if kind in (7, 8):
                intent.update(source=tree, recursive=True)
                add(intent, "content-versus-name-search", "grep-files", split,
                    source=named(tree), pattern=named(pattern), case=", ignoring letter case" if intent.get("ignore_case") else ", respecting letter case")
                continue
            action = "count" if intent.get("count") else "print, with their line numbers," if intent.get("line_numbers") else "print"
            selection = ("lines that do not contain" if intent.get("invert") else "lines containing") + " the literal text " + named(pattern)
            case = ", ignoring letter case" if intent.get("ignore_case") else ", respecting letter case"
            add(intent, "literal-search-options", "grep", split, source=named(src), action=action, action_cap=action.capitalize(), selection=selection, case=case)

        ext = ["toml", "rst", "csv", "ini", "json", "yaml", "md", "sh", "tsv", "conf"][index % 10]
        for kind in range(11):
            intent = {"op": "find", "directory": tree, "type": "d" if kind in (1, 7, 10) else "f"}
            if kind in (2, 3, 5, 7, 8, 9, 10):
                intent["pattern"] = "*." + ext
            if kind in (3, 9):
                intent["size_gt"] = [64, 128, 1024, 4096, 8192][index % 5]
            if kind in (4, 5, 10):
                intent["empty"] = True
            if kind in (6, 8, 9):
                intent["maxdepth"] = 1 if kind != 9 else 2
            selection = "directories" if intent["type"] == "d" else "regular files"
            if intent.get("empty"):
                selection = "empty " + selection
            if "pattern" in intent:
                selection += " whose names end in ." + ext
            if "size_gt" in intent:
                selection += f" and whose size is strictly greater than {intent['size_gt']} bytes"
            scope = "recursively below " + named(tree)
            if intent.get("maxdepth"):
                scope = "directly inside " + named(tree) + ", without descending into subdirectories" if intent["maxdepth"] == 1 else "below " + named(tree) + ", going no deeper than two path components from that starting directory"
            elif intent["type"] == "d":
                scope = "in the tree rooted at " + named(tree) + ", including the root itself if it matches"
            add(intent, "filesystem-filter-composition" if kind in (3, 5, 8, 9, 10) else "filesystem-filters", "find", split, selection=selection, scope=scope)

        for mode, directory, recursive in (("600", False, False), ("755", False, False), ("750", True, False), ("755", False, True)):
            targets = [tree] if directory or recursive else [src]
            intent = {"op": "chmod", "targets": targets, "mode": mode}
            if directory:
                intent["directory_target"] = True
            if recursive:
                intent["recursive"] = True
            add(intent, "permission-scope", "chmod", split, mode=mode, targets=listed(targets),
                scope=" on the entire tree, including every nested file and folder" if recursive else " on the directory itself, leaving its contents unchanged" if directory else "")

    # The tiny navigation vocabulary benefits from genuinely varied phrasing;
    # these are training-only and share known primitive labels intentionally.
    primitives = {
        "/": ["Put the terminal at the filesystem root.", "Go all the way to the top of the filesystem.",
              "I want to work in the root of the Linux directory tree.", "Take this session to the slash directory.",
              "Switch into the filesystem's root folder.", "Set my shell's directory to the topmost filesystem location."],
        "~": ["Take the terminal back to my home folder.", "Go to the personal home directory for this user.",
              "I want to work from my account's home.", "Switch the shell into my own home directory.",
              "Use my login user's home as the working folder.", "Navigate to my personal home folder in this session."],
        "..": ["Move this terminal up one directory level.", "Go to the folder containing the current one.",
               "I want to work in this folder's parent.", "Take the shell one level higher in the directory tree.",
               "Switch from this directory to its immediate parent.", "Set the current location to the enclosing directory."],
        ".": ["Keep this terminal in its current working directory.", "Change directory to this same folder.",
              "Stay at the working directory I'm already using.", "Use the present folder as the shell's directory.",
              "Switch to the directory represented by a single dot.", "Go to the current directory itself."]}
    for n, (destination, requests) in enumerate(primitives.items()):
        groups.append({"id": f"{PREFIX}cd-primitive-{n}", "family": "cd", "topic": "navigation", "capability": "root-home-parent-current", "split": "train", "intent": {"op": "cd", "destination": destination}, "requests": requests})

    # Teach deictic language across search and listing, using training wording only.
    # Exclusion uses benchmark labels solely as a firewall, never as templates.
    reserved = {json.loads(line)["reference"] for p in (DATA.parent.parent / "eval").glob("*/cases.jsonl")
                for line in p.read_text(encoding="utf-8").splitlines() if line.strip()}
    for ext in ("toml", "rst", "csv", "ini", "json", "yaml", "md", "sh", "tsv", "conf"):
        for depth in (None, 1, 2):
            intent = {"op": "find", "directory": ".", "type": "f", "pattern": "*." + ext}
            if depth:
                intent["maxdepth"] = depth
            if render(intent) in reserved:
                continue
            scope = "here and in all folders below the current directory" if depth is None else "directly in this working folder, without entering subfolders" if depth == 1 else "under the current directory, going at most two levels deep"
            add(intent, "current-location-search", "find", "train", selection="regular files with names ending in ." + ext, scope=scope)
    for all_entries, long, one in ((False, False, False), (True, False, False), (False, True, False), (True, True, False), (False, False, True), (True, False, True)):
        slots = dict(place="here in the current directory", items="all entries including hidden names" if all_entries else "only non-hidden entries",
                     style=" with detailed permissions, ownership and sizes" if long else " with exactly one entry on each line" if one else "")
        groups.append({"id": f"{PREFIX}ls-current-{int(all_entries)}{int(long)}{int(one)}", "family": "ls", "topic": "filesystem",
                       "capability": "current-location-listing", "split": "train",
                       "intent": {"op": "ls", "directory": ".", "all": all_entries, "long": long, "one": one},
                       "requests": [form.format(**slots) for form in PHRASES["ls"][0]]})
    return groups


def main():
    target = DATA / "catalogs" / RELEASE
    if (DATA / "releases" / RELEASE).exists():
        raise SystemExit("A rendered pilot-v2 exists; preserve it and author a new release.")
    groups = author()
    sourced = [dict(g, source=f"data/shell_translation/catalogs/{RELEASE}/{g['topic']}/{g['family']}.json") for g in groups]
    records = compile_examples(sorted(sourced, key=lambda g: (g["source"], g["id"])), RELEASE)
    summary = check_records(records)
    shards = defaultdict(list)
    for group in groups:
        shards[target / group["topic"] / (group["family"] + ".json")].append(group)
    for filename, content in shards.items():
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    new = [g for g in groups if g["id"].startswith(PREFIX)]
    report = {"date": "2026-10-10", "release": RELEASE, "parent_release": "pilot-v1",
              "parent_dataset_sha256": json.loads((DATA / "releases/pilot-v1/manifest.json").read_text())["dataset_sha256"],
              "inherited_groups": len(groups) - len(new), "added_groups": len(new),
              "added_examples": sum(len(g["requests"]) for g in new),
              "added_splits": dict(Counter(g["split"] for g in new)),
              "added_family_groups": dict(Counter(g["family"] for g in new)),
              "added_capability_groups": dict(Counter(g["capability"] for g in new)),
              "training_argument_roots": TRAIN_NAMES, "validation_argument_roots": VALIDATION_NAMES,
              "method": "authored semantic matrix with literal-argument and sentence-bank holdouts",
              "benchmark_use": "latest ShellBench v1 aggregate failures identified broad capabilities; no benchmark requests used as authoring sources; Extra used only by exclusion audits",
              "summary": summary}
    # Metadata lives outside catalog JSON arrays so source_groups stays strict.
    metadata = DATA / "authoring" / RELEASE
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "coverage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("training_argument_roots", "validation_argument_roots", "summary")}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
