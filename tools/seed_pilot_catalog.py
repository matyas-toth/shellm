"""Author the initial command-first catalogs once; editable JSON becomes authoritative."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / "data" / "shell_translation" / "catalogs" / "pilot-v1"
NAMES = ["copper", "mango", "falcon", "orchid", "nebula", "otter", "cedar", "saffron", "marble", "comet",
         "willow", "badger", "quartz", "hazel", "maple", "raven", "lotus", "birch", "tundra", "zephyr"]
TOPICS = {"pwd": "navigation", "cd": "navigation", "find": "search",
          **{name: "filesystem" for name in ("ls", "mkdir", "touch", "cp", "mv", "rm")},
          **{name: "text" for name in ("cat", "head", "tail", "wc", "grep")}}

PWD_REQUESTS = [
    ["print my present directory path", "which directory is this terminal using?", "give the full pathname of this working folder", "show the shell's present directory"],
    ["I need the absolute name of my current folder", "write out this folder's full filesystem path", "output the path I am working from", "identify the directory this shell is in"],
    ["what is my present working folder?", "display the full directory name for this location", "show me this session's working path", "print the filesystem location of this terminal"],
    ["get the absolute pathname for the working folder", "tell me which directory the shell currently occupies", "what directory path is active here?", "write the current folder location to stdout"],
    ["show this terminal's absolute directory path", "what's the complete name of the folder I'm in?", "output the pathname of the working directory", "give my shell's current folder location"],
    ["display my present filesystem location", "print the path for the folder this session uses", "which folder does this shell currently point at?", "show the absolute working-folder pathname"],
    ["retrieve my terminal's working directory", "I want to see the folder path for this shell", "report the current directory as a full path", "what path is this session working inside?"],
    ["show me the current working folder's name in full", "display the directory pathname for this terminal", "which absolute folder path am I using?", "print out the shell's working location"],
    ["get the full filesystem path for my working folder", "what's the shell's present location on disk?", "show the current directory pathname in the terminal", "tell me the full directory location of this session"],
    ["output this session's active folder path", "print the folder location where commands are running", "show the full path of the shell's active directory", "what is the complete working-directory pathname?"],
    ["can you print this working folder's absolute path?", "let me see the pathname of the directory I'm in", "report the directory this terminal is working from", "output my present folder as a full path"],
    ["I need to check my shell's working location", "print the full location of the active directory", "which directory is active in this terminal?", "display the current folder as an absolute pathname"],
    ["what full path corresponds to this working directory?", "show this shell session's directory location", "write out my present working-folder path", "display the full path that this terminal is using"],
    ["need to know the pathname of my working folder", "print this session's current folder location", "get the shell's active directory path", "what absolute directory am I standing in?"],
    ["report the pathname of this shell's working folder", "show the full location of my terminal session", "give the absolute directory name for this shell", "print my active folder's filesystem pathname"],
    ["where is the working folder for this terminal session?", "display the directory path currently used by the shell", "output the complete location of the current folder", "tell me the terminal's active directory pathname"],
    ["I'd like the full path of this session's folder", "write the shell's current directory path", "what pathname identifies this working folder?", "print the directory location for the active terminal"],
    ["show the absolute location of the working directory", "get me this terminal's present folder path", "report my current working location as a pathname", "which full directory name is this shell using?"],
    ["locate this shell session by printing its directory path", "give me the pathname for my present working location", "write the absolute folder location of the terminal", "display which directory this session is operating in"],
    ["show this session's location as a complete directory path", "what is the absolute pathname of my active folder?", "print the location from which this shell runs commands", "identify my present working directory by its full pathname"],
]


def catalog(family):
    groups = []
    for index, noun in enumerate(NAMES):
        op, capability = {"op": family}, "basic"
        if family == "pwd":
            requests = PWD_REQUESTS[index]
            capability = "phrasing"
        elif family == "cd":
            if index == 0:
                destination, target = "/", "the filesystem's top-level directory"
            elif index == 1:
                destination, target = "~", "my user's home folder"
            elif index == 2:
                destination, target = "..", "the parent of this directory"
            else:
                destination = ("/workspace/" if index % 4 == 0 else "") + (f"{noun} workspace" if index % 3 == 0 else f"{noun}-area")
                if index == 7:
                    destination = "client's saffron folder"
                if index == 10:
                    destination = "-willow-area"
                target = f"the directory named {destination}"
            op["destination"] = destination
            requests = [f"change the working directory to {target}", f"navigate into {target}", f"switch folders to {target}", f"take this shell to {target}"]
            capability = "navigation"
        elif family == "ls":
            flags = index % 5
            directory = "." if index < 5 else (f"{noun} catalog" if index % 3 == 0 else f"catalog-{noun}")
            op.update(directory=directory, all=flags in (1, 3), long=flags in (2, 3), one=flags == 4)
            description = "every entry including hidden entries" if op["all"] else "the non-hidden entries"
            extra = " with a long detailed listing" if op["long"] else " with one entry per line" if op["one"] else ""
            target = "this working folder" if directory == "." else directory
            requests = [f"list {description} in {target}{extra}", f"show {description} inside {target}{extra}",
                        f"display {description} from {target}{extra}", f"give me {description} in {target}{extra}"]
            capability = "listing-options"
        elif family == "mkdir":
            mode = index % 5
            targets = [f"{noun}-folder"]
            if mode == 1:
                targets = [f"{noun} drafts"]
            if mode == 2:
                targets = [f"build-{noun}/cache/results"]
                op["parents"] = True
            if mode == 3:
                targets = [f"{noun}-one", f"{noun}-two"]
            if mode == 4:
                op["mode"] = "700"
            if index == 5:
                targets = ["-otter-folder"]
            op["targets"] = targets
            description = "directories named " + " and ".join(targets) if len(targets) > 1 else "a directory named " + targets[0]
            suffix = " and create any missing parents" if op.get("parents") else " with permissions 700" if op.get("mode") else ""
            requests = [f"create {description}{suffix}", f"make {description}{suffix}", f"I need {description}{suffix}", f"set up {description}{suffix}"]
            capability = "directory-creation"
        elif family == "touch":
            targets = [f"{noun}.new"]
            if index % 4 == 0:
                targets = [f"{noun} scratch.txt"]
            elif index % 4 == 1:
                targets = [f"blanks/{noun}.txt"]
            elif index % 4 == 2:
                targets = [f"{noun}-a.txt", f"{noun}-b.txt"]
            if index == 7:
                targets = ["client's saffron scratch.txt"]
            if index == 11:
                targets = ["-badger.new"]
            op["targets"] = targets
            description = "empty files named " + " and ".join(targets) if len(targets) > 1 else "an empty file named " + targets[0]
            requests = [f"create {description}", f"make {description}", f"I need {description}", f"add {description} to the filesystem"]
            capability = "empty-file-creation"
        elif family in ("cp", "mv"):
            kind = index % 5
            source = f"inputs/{noun}.txt"
            destination = f"outputs/{noun}-saved.txt"
            if kind == 1:
                source = f"{noun} reading notes.txt"
                destination = f"{noun} saved notes.txt"
            if kind == 2:
                destination = f"stash-{noun}"
                op["into"] = True
            if kind == 3:
                op["into"] = True
                destination = f"stash-{noun}"
            if kind == 4:
                op["directory_source"] = True
                source, destination = f"bundle-{noun}", f"saved-{noun}"
            if index == 10:
                source = "-willow-source.txt"
            if index == 16:
                source = "client's lotus source.txt"
            sources = [source, f"inputs/{noun}-extra.txt"] if kind == 3 else [source]
            op.update(sources=sources, destination=destination)
            subject = "the directory " + source + " and all its contents" if op.get("directory_source") else "the file " + sources[0] if len(sources) == 1 else "the files " + " and ".join(sources)
            target = f"into {destination}" if op.get("into") else f"to {destination}"
            if family == "cp":
                requests = [f"copy {subject} {target}", f"make a copy of {subject} {target}", f"duplicate {subject} {target}", f"put a copy of {subject} {target}"]
            else:
                requests = [f"move {subject} {target}", f"relocate {subject} {target}", f"put {subject} {target} and remove the original location", f"transfer {subject} {target} without keeping the original"]
            capability = "copy" if family == "cp" else "move-or-rename"
        elif family == "rm":
            recursive = index % 4 == 0
            targets = [f"discard-{noun}"] if recursive else [f"{noun}.old"]
            if index % 4 == 1:
                targets = [f"{noun} old memo.txt"]
            if index % 4 == 2:
                targets = [f"{noun}-a.old", f"{noun}-b.old"]
            if index == 11:
                targets = ["-badger.old"]
            if index == 15:
                targets = ["client's raven old memo.txt"]
            op.update(targets=targets, recursive=recursive)
            subject = "the directory " + targets[0] + " and everything inside it" if recursive else "the file " + targets[0] if len(targets) == 1 else "the files " + " and ".join(targets)
            requests = [f"delete {subject}", f"remove {subject}", f"erase {subject}", f"get rid of {subject}"]
            capability = "removal"
        elif family == "cat":
            sources = [f"texts/{noun}.txt"]
            if index % 4 == 0:
                sources = [f"{noun} text.txt"]
            if index % 4 == 2:
                sources.append(f"texts/{noun}-extra.txt")
            if index == 7:
                sources = ["client's saffron text.txt"]
            if index == 11:
                sources = ["-badger-text.txt"]
            op["sources"] = sources
            subject = "the entire contents of " + " then ".join(sources) + (" in that order" if len(sources) > 1 else "")
            requests = [f"print {subject}", f"display {subject}", f"show me {subject}", f"write {subject} to standard output"]
            capability = "read-full-files"
        elif family in ("head", "tail"):
            source = f"texts/{noun}.txt" if index % 4 else f"{noun} text.txt"
            count = index % 10 + 1
            byte_mode = index in (5, 15)
            op.update(source=source, count=count, bytes=byte_mode)
            end = "first" if family == "head" else "last"
            unit = "bytes" if byte_mode else "lines"
            requests = [f"print the {end} {count} {unit} of {source}", f"show only the {end} {count} {unit} from {source}",
                        f"display the {end} {count} {unit} in {source}", f"give me the {end} {count} {unit} of the file {source}"]
            capability = "text-slicing"
        elif family == "wc":
            unit = ("lines", "words", "bytes")[index % 3]
            source = f"texts/{noun}.txt" if index % 4 else f"{noun} text.txt"
            op.update(source=source, unit=unit)
            requests = [f"count {unit} in {source}", f"how many {unit} are in {source}?", f"get the number of {unit} in {source}", f"report the {unit} count for {source}"]
            capability = "count-text"
        elif family == "grep":
            mode = index % 6
            pattern = ["WARN", "a.b", "READY", "fatal.error", "todo_7", "[notice]"][index % 6]
            source = f"search-{noun}" if mode == 5 else (f"{noun} messages.txt" if index % 4 == 0 else f"texts/{noun}.txt")
            op.update(source=source, pattern=pattern)
            if mode == 1:
                op["ignore_case"] = True
            if mode == 2:
                op["line_numbers"] = True
            if mode == 3:
                op["invert"] = True
            if mode == 4:
                op["count"] = True
            if mode == 5:
                op["recursive"] = True
                subject = f"file paths containing the literal text {pattern} recursively under {source}"
                requests = [f"list the {subject}", f"find the {subject}", f"show the {subject}", f"print the {subject}"]
            else:
                relation = "not containing" if mode == 3 else "containing"
                subject = f"lines {relation} the literal text {pattern} in {source}"
                suffix = " ignoring case" if mode == 1 else " with their line numbers" if mode == 2 else ""
                verbs = ["count", "get the number of", "report the count of", "tell me how many"] if mode == 4 else ["print", "show", "display", "output"]
                requests = [f"{verb} {subject}{suffix}" for verb in verbs]
            capability = "literal-text-search"
        elif family == "find":
            mode = index % 5
            directory = f"tree {noun}" if index % 3 == 0 else f"tree-{noun}"
            extension = ("cfg", "txt", "py", "md", "log")[index % 5]
            op.update(directory=directory, type="d" if mode == 1 else "f")
            if mode in (0, 4):
                op["pattern"] = f"*.{extension}"
            if mode == 2:
                op["maxdepth"] = 1
            if mode == 3:
                op["empty"] = True
            if mode == 4:
                op["size_gt"] = 100 + (index % 3) * 25
            subject = "all directories including the starting directory" if mode == 1 else "empty regular files" if mode == 3 else "regular files"
            if op.get("pattern"):
                subject += f" ending in .{extension}"
            if op.get("size_gt"):
                subject += f" larger than {op['size_gt']} bytes"
            location = f"directly inside {directory} without searching subdirectories" if mode == 2 else f"recursively starting at {directory}"
            requests = [f"find {subject} {location}", f"list {subject} {location}", f"show the paths of {subject} {location}", f"locate {subject} {location}"]
            capability = "filesystem-search"
        else:
            raise ValueError(family)
        groups.append({"id": f"pilot-v1-{family}-{index + 1:02d}", "topic": TOPICS[family], "family": family,
                       "capability": capability, "split": "validation" if index >= 18 else "train",
                       "intent": op, "requests": requests})
    return groups


def main():
    if DESTINATION.exists():
        raise SystemExit("Catalog already exists; edit the JSON catalogs or use a new release")
    for family in TOPICS:
        target = DESTINATION / TOPICS[family] / f"{family}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(catalog(family), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Authored 280 intent groups in {DESTINATION}")


if __name__ == "__main__":
    main()
