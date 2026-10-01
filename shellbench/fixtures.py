"""Deterministic filesystem fixtures shared by trusted and candidate runs."""

def fixture(seed: int) -> dict:
    names = ["amber", "violet"] if seed == 0 else ["cobalt", "silver", "green"]
    notes = "\n".join([
        f"hello {names[0]}", "TODO: review this", "a.b literal", "axb decoy",
        "todo: lowercase", "done", *[f"extra {name}" for name in names],
    ]) + "\n"
    return {
        "directories": ["docs", "src", "archive", "empty", "obsolete/nested",
                        "my projects", "client's files", ".hidden-dir", "directory.log", "directory.py"],
        "files": {
            "notes.txt": notes,
            "report.txt": "\n".join(f"row {i}: {name}" for i, name in enumerate(names, 1)) + "\n",
            "README.md": "\n".join(f"readme line {i} {names[0]}" for i in range(1, 13 + seed)) + "\n",
            "numbers.txt": "\n".join(str(i) for i in range(1, 18 + seed)) + "\n",
            "unicode.txt": "café naïve\nhello 世界\n",
            "todo list.txt": f"buy {names[0]}\nTODO: write notes\n",
            "client's plan.txt": f"plan for {names[-1]}\n",
            "-draft.txt": "draft\n",
            "empty.txt": "",
            "old.log": ("old event\n" * (20 + seed)),
            "app.log": "new event\n",
            "UPPER.LOG": "upper extension\n",
            "docs/intro.md": f"Introduction {names[0]}\nTODO: improve docs\n",
            "docs/old.log": "nested event\n",
            "src/main.py": "print('hello')\n# TODO: add tests\n",
            "src/main.log": "source event\n",
            "src/helper.py": "# helper\n",
            "obsolete/nested/keep.txt": "remove with obsolete directory\n",
            "archive/keep.txt": "preserve me\n",
            ".hidden": "hidden content\n",
            "my projects/plan.txt": "project plan\n",
        },
        "symlinks": {"notes.link": "notes.txt"},
        "home_files": {"home-note.txt": f"home {names[0]}\n"},
    }
