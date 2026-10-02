"""New filesystem worlds for Extra v1; no training fixture or catalog imports."""


def fixture(seed):
    messages = ["[ok] startup", "WARN: slow network", "FAIL: disk full", "fail: lowercase",
                "needle.a literal", "needlexa decoy", "A+B literal", "AB decoy", "[ok] shutdown",
                "pending review", "reviewed item", "FAIL: connection lost"]
    if seed:
        messages += ["FAIL: extra incident", "WARN: retry", "pending approval"]
    amounts = [11, 2, 37, 2, -4, 11] + ([19, 2] if seed else [])
    words = ["pear", "kiwi", "lime", "pear", "kiwi", "pear", "fig"] + (["fig", "lime"] if seed else [])
    rows = ["Ari\tred\t7", "Bea\tblue\t12", "Cai\tred\t3", "Dee\tgreen\t21"]
    if seed:
        rows += ["Eli\tblue\t9", "Fay\tred\t18"]
    files = {
        "lab/messages.txt": "\n".join(messages) + "\n",
        "lab/amounts.txt": "\n".join(map(str, amounts)) + "\n",
        "lab/words.txt": "\n".join(words) + "\n",
        "lab/ledger.tsv": "name\tteam\tscore\n" + "\n".join(rows) + "\n",
        "lab/cities.csv": "id,city,active\n1,Oslo,yes\n2,Lima,no\n3,Kyoto,yes\n" + ("4,Riga,yes\n" if seed else ""),
        "lab/prose.txt": "heading\nfirst detail\n\n# private comment\nsecond detail\nlast detail\n" + ("added detail\n" if seed else ""),
        "lab/spaced.txt": "  red   blue\n\tgreen\tgold\nblank     gaps\n",
        "lab/mixed.txt": "Hello THERE\nMixed 123 text\n",
        "lab/left.txt": "north\nsouth\neast\n" + ("west\n" if seed else ""),
        "lab/right.txt": "10\n20\n30\n" + ("40\n" if seed else ""),
        "lab/client files/quarter one.txt": f"quarter plan variant {seed}\n",
        "lab/client files/director's note.txt": f"director memo variant {seed}\n",
        "lab/client files/[draft]*.txt": "literal bracket and star filename\n",
        "lab/client files/draftA.txt": "glob decoy; preserve me\n",
        "lab/client files/$budget.txt": "literal dollar filename\n",
        "lab/client files/a;b.txt": "literal semicolon ; filename\n",
        "lab/client files/-receipt.txt": "leading dash filename\n",
        "lab/client files/café.txt": "naïve café\n世界\n",
        "lab/client files/odd & ends.txt": "literal ampersand filename\n",
        "lab/client files/report (final).txt": "literal parentheses filename\n",
        "lab/client files/$(printf oops).txt": "literal substitution filename\n",
        "lab/raw/readme.txt": "raw source notes\n",
        "lab/raw/sub/chunk.txt": f"chunk payload {seed}\n",
        "lab/archive/stay.txt": "archive sentinel; preserve me\n",
        "lab/work/stay.txt": "work sentinel; preserve me\n",
        "lab/logs/error one.log": "FAIL incident\n" * (12 + seed),
        "lab/logs/okay.log": "ordinary activity\n",
        "lab/logs/.secret.log": "private event\n",
        "lab/logs/boundary.log": "x" * (99 if seed == 0 else 101),
        "lab/logs/nested/deep.log": "FAIL nested\n" * (20 + seed),
        "lab/logs/skip/noise.log": "noise\n" * 70,
        "lab/logs/unrelated.txt": "large but wrong extension\n" * 30,
        "lab/scan/tiny.dat": "z" * (8 + seed),
        "lab/scan/large.dat": "z" * (160 + seed),
        "lab/scan/empty.dat": "",
        "lab/scan/.hidden.dat": "hidden\n",
        "lab/scan/UPPER.DAT": "uppercase extension\n",
        "lab/scan/one.py": "# FIXME: first\nprint(1)\n",
        "lab/scan/nested/two.py": "# FIXME: nested\nprint(2)\n",
        "lab/scan/nested/plain.txt": "text only\n",
        "lab/scan/nested/zero.txt": "",
        "lab/scan/vendor/ignored.py": "# FIXME: vendor\n",
        "lab/.concealed.txt": "hidden at lab root\n",
        "lab/.private/inside.txt": "hidden subtree\n",
        "sentinel-extra.txt": "whole-workspace sentinel\n",
    }
    if seed == 0:
        files["lab/gate.ok"] = "gate present\n"
    else:
        files["lab/scan/nested/added.dat"] = "variant-specific datum\n"
    return {
        "directories": ["lab", "lab/client files", "lab/raw", "lab/raw/sub", "lab/archive", "lab/work",
                        "lab/logs", "lab/logs/nested", "lab/logs/skip", "lab/logs/not-a-file.log",
                        "lab/scan", "lab/scan/nested", "lab/scan/vendor", "lab/scan/directory.dat",
                        "lab/.private", "lab/empty vault", "lab/scan/empty-directory"],
        "files": files,
        "symlinks": {"lab/raw-shortcut": "raw", "lab/scan/link.dat": "large.dat"},
        "home_files": {"welcome-extra.txt": f"welcome variant {seed}\n"},
    }
