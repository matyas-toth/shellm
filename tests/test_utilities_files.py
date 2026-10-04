"""File and path command families: render, validation, and Docker-backed oracle behavior."""

import unittest

from shellm_data.intents import render, validate_intent

try:
    from .utility_helpers import UtilityCase
except ImportError:
    from utility_helpers import UtilityCase


class FileCase(UtilityCase):
    def assert_invalid(self, *intents):
        for intent in intents:
            with self.assertRaises(ValueError, msg=intent):
                validate_intent(intent)

    def assert_accepts(self, intent, *commands):
        for command in commands:
            self.assertTrue(self.accepts(intent, command), command)

    def assert_rejects(self, intent, *commands):
        for command in commands:
            self.assertFalse(self.accepts(intent, command), command)


class LnTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "ln", "source": "notes.txt", "destination": "notes-link", "symbolic": True}),
                         "ln -s notes.txt notes-link")
        self.assertEqual(render({"op": "ln", "source": "-a.txt", "destination": "b link"}), "ln -- -a.txt 'b link'")
        self.assert_invalid({"op": "ln", "source": "a"}, {"op": "ln", "source": "a", "destination": "a"},
                            {"op": "ln", "source": "a", "destination": "b", "bogus": True})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "ln", "source": "notes.txt", "destination": "notes-link", "symbolic": True}
        self.assert_accepts(intent, "ln -s notes.txt notes-link", "ln -sf -- notes.txt notes-link")
        self.assert_rejects(intent, "ln notes.txt notes-link", "ln -s ./notes.txt notes-link", "ln -s notes.txt other-link")
        hard = {"op": "ln", "source": "notes.txt", "destination": "copy.txt"}
        self.assert_accepts(hard, "ln notes.txt copy.txt")
        self.assert_rejects(hard, "ln -s notes.txt copy.txt")

    def test_more_capabilities(self):
        force = {"op": "ln", "source": "settings.json", "destination": "current.json", "symbolic": True, "force": True}
        self.assert_accepts(force, "ln -sf settings.json current.json", "ln -s -f -- settings.json current.json")
        self.assert_rejects(force, "ln -s settings.json current.json", "ln -f settings.json current.json")
        nested = {"op": "ln", "source": "../data/my notes.txt", "destination": "links/client's notes", "symbolic": True}
        self.assert_accepts(nested, "ln -s '../data/my notes.txt' \"links/client's notes\"")
        self.assert_rejects(nested, "ln -s 'data/my notes.txt' \"links/client's notes\"")
        hard = {"op": "ln", "source": "a.txt", "destination": "b.txt", "force": True}
        self.assert_accepts(hard, "ln -f a.txt b.txt")
        self.assert_rejects(hard, "ln a.txt b.txt", "ln -sf a.txt b.txt")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "ln")


class LinkTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "link", "source": "report.txt", "destination": "hard.txt"}), "link report.txt hard.txt")
        self.assert_invalid({"op": "link", "source": "a"}, {"op": "link", "source": "a", "destination": "a"})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "link", "source": "report.txt", "destination": "hard.txt"}
        self.assert_accepts(intent, "link report.txt hard.txt", "ln report.txt hard.txt")
        self.assert_rejects(intent, "ln -s report.txt hard.txt", "touch hard.txt", "mv report.txt hard.txt")

    def test_more_capabilities(self):
        nested = {"op": "link", "source": "docs/report.txt", "destination": "backup/report.txt"}
        self.assert_accepts(nested, "link docs/report.txt backup/report.txt", "ln docs/report.txt backup/report.txt")
        self.assert_rejects(nested, "link docs/report.txt report.txt")
        dash = {"op": "link", "source": "-draft.txt", "destination": "draft-link.txt"}
        self.assert_accepts(dash, "link -- -draft.txt draft-link.txt", "ln -- -draft.txt draft-link.txt")
        self.assert_rejects(dash, "ln -s -- -draft.txt draft-link.txt")
        # The state snapshot has no inode or link count, so a copy is indistinguishable from a hard link.
        # No catalog: natural hard-link requests belong to ln.


class UnlinkTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "unlink", "target": "old draft.txt"}), "unlink 'old draft.txt'")
        self.assert_invalid({"op": "unlink"}, {"op": "unlink", "target": ["a"]})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "unlink", "target": "old.txt"}
        self.assert_accepts(intent, "unlink old.txt", "rm old.txt")
        self.assert_rejects(intent, "true", "rm old.txt keep/untouched.txt", "mv old.txt old.bak")

    def test_more_capabilities(self):
        link = {"op": "unlink", "target": "current.link", "symlink": True}
        self.assert_accepts(link, "unlink current.link", "rm current.link")
        self.assert_rejects(link, "rm current.link original.txt", "rm original.txt")
        nested = {"op": "unlink", "target": "logs/old/app.log"}
        self.assert_accepts(nested, "unlink logs/old/app.log")
        self.assert_rejects(nested, "rm -r logs")
        self.assert_invalid({"op": "unlink", "target": "a", "symlink": "yes"})
        # No catalog: natural file-removal requests belong to rm.


class RmdirTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "rmdir", "targets": ["empty-folder", "old stuff"]}), "rmdir empty-folder 'old stuff'")
        self.assert_invalid({"op": "rmdir", "targets": []}, {"op": "rmdir", "targets": ["a", "a/b"]})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "rmdir", "targets": ["empty-folder"]}
        self.assert_accepts(intent, "rmdir empty-folder", "rm -d empty-folder")
        self.assert_rejects(intent, "true", "rm -r empty-folder keep", "mkdir other")

    def test_more_capabilities(self):
        parents = {"op": "rmdir", "targets": ["reports/2024/drafts"], "parents": True}
        self.assertEqual(render(parents), "rmdir -p reports/2024/drafts")
        self.assert_accepts(parents, "rmdir -p reports/2024/drafts", "rmdir reports/2024/drafts reports/2024 reports")
        self.assert_rejects(parents, "rmdir reports/2024/drafts", "rm -r reports/2024")
        multiple = {"op": "rmdir", "targets": ["empty-one", "empty-two"]}
        self.assert_accepts(multiple, "rmdir empty-one empty-two")
        self.assert_rejects(multiple, "rmdir empty-one")
        self.assert_invalid({"op": "rmdir", "targets": ["flat"], "parents": True})

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "rmdir")


class ReadlinkTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "readlink", "source": "notes.link"}), "readlink notes.link")
        self.assert_invalid({"op": "readlink"}, {"op": "readlink", "source": ""})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "readlink", "source": "notes.link"}
        self.assert_accepts(intent, "readlink notes.link", "readlink -- notes.link")
        self.assert_rejects(intent, "readlink -f notes.link", "realpath notes.link", "echo notes.link")

    def test_more_capabilities(self):
        # The raw target differs per fixture seed, so a hard-coded answer fails; resolving belongs to realpath.
        intent = {"op": "readlink", "source": "notes.link"}
        self.assert_rejects(intent, "echo versions/v1/original.txt", "readlink -e notes.link", "ls -l notes.link")
        self.assert_invalid({"op": "readlink", "source": "notes.link", "canonicalize": True})
        nested = {"op": "readlink", "source": "links/latest"}
        self.assert_accepts(nested, "readlink links/latest", "(cd links && readlink latest)")
        self.assert_rejects(nested, "readlink -f links/latest", "cd links && readlink latest")
        dash = {"op": "readlink", "source": "-latest build"}
        self.assert_accepts(dash, "readlink -- '-latest build'", "readlink './-latest build'")
        self.assert_rejects(dash, "readlink -latest build")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "readlink")


class RealpathTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "realpath", "source": "docs/intro.md"}), "realpath docs/intro.md")
        self.assert_invalid({"op": "realpath"}, {"op": "realpath", "source": "a", "bogus": 1})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "realpath", "source": "docs/intro.md"}
        self.assert_accepts(intent, "realpath docs/intro.md", "readlink -f docs/intro.md")
        self.assert_rejects(intent, "echo docs/intro.md", "realpath docs", "dirname docs/intro.md")

    def test_more_capabilities(self):
        relative = {"op": "realpath", "source": "reports/q1 summary.txt", "relative_to": "reports"}
        self.assertEqual(render(relative), "realpath --relative-to=reports 'reports/q1 summary.txt'")
        self.assert_accepts(relative, "realpath --relative-to=reports 'reports/q1 summary.txt'")
        self.assert_rejects(relative, "realpath 'reports/q1 summary.txt'", "realpath --relative-to=. 'reports/q1 summary.txt'")
        dots = {"op": "realpath", "source": "docs/../notes.txt"}
        self.assert_accepts(dots, "realpath docs/../notes.txt", "readlink -f docs/../notes.txt")
        self.assert_rejects(dots, "echo docs/../notes.txt", "realpath docs")
        link = {"op": "realpath", "source": "links/current", "symlink": True}
        self.assert_accepts(link, "realpath links/current", "readlink -f links/current")
        self.assert_rejects(link, "readlink links/current", "realpath -s links/current")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "realpath")


class BasenameTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "basename", "source": "docs/intro.md", "suffix": ".md"}), "basename docs/intro.md .md")
        self.assertEqual(render({"op": "basename", "source": "docs/intro.md"}), "basename docs/intro.md")
        self.assert_invalid({"op": "basename"}, {"op": "basename", "source": "a", "suffix": ""})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "basename", "source": "docs/intro.md", "suffix": ".md"}
        self.assert_accepts(intent, "basename docs/intro.md .md", "basename -s .md docs/intro.md")
        self.assert_rejects(intent, "basename docs/intro.md", "dirname docs/intro.md")
        self.assert_accepts({"op": "basename", "source": "docs/intro.md"}, "basename docs/intro.md")

    def test_more_capabilities(self):
        plain = {"op": "basename", "source": "/usr/local/bin/backup.sh"}
        self.assert_accepts(plain, "basename /usr/local/bin/backup.sh")
        self.assert_rejects(plain, "dirname /usr/local/bin/backup.sh", "basename -s .sh /usr/local/bin/backup.sh")
        slash = {"op": "basename", "source": "reports/2024/"}
        self.assert_accepts(slash, "basename reports/2024/")
        self.assert_rejects(slash, "dirname reports/2024/")
        quoted = {"op": "basename", "source": "my docs/client's Q1 report.pdf", "suffix": ".pdf"}
        self.assert_accepts(quoted, "basename -s .pdf \"my docs/client's Q1 report.pdf\"")
        self.assert_rejects(quoted, "basename \"my docs/client's Q1 report.pdf\"")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "basename")


class DirnameTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "dirname", "source": "docs/intro.md"}), "dirname docs/intro.md")
        self.assert_invalid({"op": "dirname"}, {"op": "dirname", "source": ["a"]})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "dirname", "source": "docs/intro.md"}
        self.assert_accepts(intent, "dirname docs/intro.md", "dirname -- docs/intro.md")
        self.assert_rejects(intent, "basename docs/intro.md", "dirname docs")
        self.assert_accepts({"op": "dirname", "source": "notes.txt"}, "dirname notes.txt")

    def test_more_capabilities(self):
        absolute = {"op": "dirname", "source": "/usr/local/bin/backup.sh"}
        self.assert_accepts(absolute, "dirname /usr/local/bin/backup.sh")
        self.assert_rejects(absolute, "dirname usr/local/bin/backup.sh", "dirname /usr/local/bin")
        quoted = {"op": "dirname", "source": "my docs/client's notes.txt"}
        self.assert_accepts(quoted, "dirname \"my docs/client's notes.txt\"")
        self.assert_rejects(quoted, "basename \"my docs/client's notes.txt\"")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "dirname")


class StatTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "stat", "source": "notes.txt", "format": "permissions"}), "stat -c %a notes.txt")
        self.assertEqual(render({"op": "stat", "source": "report.csv", "format": "owner"}), "stat -c %U report.csv")
        self.assertEqual(render({"op": "stat", "source": "draft.md", "format": "modified"}), "stat -c %y draft.md")
        # Byte size belongs to wc, so stat does not offer it.
        self.assert_invalid({"op": "stat", "source": "a"}, {"op": "stat", "source": "a", "format": "size"},
                            {"op": "stat", "source": "a", "format": "inode"})

    def test_equivalent_and_wrong_commands(self):
        permissions = {"op": "stat", "source": "notes.txt", "format": "permissions"}
        self.assert_accepts(permissions, "stat -c %a notes.txt", "stat --format=%a notes.txt")
        self.assert_rejects(permissions, "stat -c %A notes.txt", "stat -c %s notes.txt", "stat -c %a keep")
        kind = {"op": "stat", "source": "docs", "format": "type", "directory": True}
        self.assertEqual(render(kind), "stat -c %F docs")
        self.assert_accepts(kind, "stat -c %F docs", "stat --printf='%F\\n' docs")
        self.assert_rejects(kind, "stat -c %a docs", "stat -c %F docs/inside.txt")

    def test_more_capabilities(self):
        # Fixture entries belong to the user running the command, so `whoami` would also pass here.
        owner = {"op": "stat", "source": "report.csv", "format": "owner"}
        self.assert_accepts(owner, "stat -c %U report.csv", "stat --format=%U report.csv")
        self.assert_rejects(owner, "stat -c %u report.csv", "ls -l report.csv")
        modified = {"op": "stat", "source": "draft.md", "format": "modified"}
        self.assert_accepts(modified, "stat -c %y draft.md", "stat --format=%y draft.md")
        self.assert_rejects(modified, "stat -c %Y draft.md", "stat -c %z draft.md", "date -r draft.md")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "stat")


class DuTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "du", "source": "docs", "summary": True, "human": True}), "du -sh docs")
        self.assertEqual(render({"op": "du", "source": "projects", "summary": True}), "du -sk projects")
        self.assertEqual(render({"op": "du", "source": "site", "max_depth": 1, "human": True}), "du -h --max-depth=1 site")
        self.assertEqual(render({"op": "du", "source": "my photos", "all": True, "human": True}), "du -ah 'my photos'")
        self.assert_invalid({"op": "du"}, {"op": "du", "source": "a", "summary": True, "all": True},
                            {"op": "du", "source": "a", "summary": True, "max_depth": 1},
                            {"op": "du", "source": "a", "max_depth": 0}, {"op": "du", "source": "a/", "summary": True},
                            {"op": "du", "source": "a", "unit": "human"})

    def test_human_size(self):
        from shellm_data.utilities.files import human_size
        self.assertEqual([human_size(n) for n in (0, 4096, 12288, 1048575, 1048576, 1572864, 11 * 1048576)],
                         ["0", "4.0K", "12K", "1.0M", "1.0M", "1.5M", "11M"])

    def test_equivalent_and_wrong_commands(self):
        # Disk usage on tmpfs: whole 4 KiB pages per file, nothing for directories; apparent sizes differ.
        total = {"op": "du", "source": "docs", "summary": True, "human": True}
        self.assert_accepts(total, "du -sh docs", "du -hs docs", "du -h --max-depth=0 docs")
        self.assert_rejects(total, "du -sh --apparent-size docs", "du -sk docs", "du -sh docs/data")
        kib = {"op": "du", "source": "projects", "summary": True}
        self.assert_accepts(kib, "du -sk projects", "du -s projects")
        self.assert_rejects(kib, "du -sb projects", "du -sh projects", "du -sm projects")
        here = {"op": "du", "source": ".", "summary": True, "human": True}
        self.assert_accepts(here, "du -sh .", "du -sh")

    def test_more_capabilities(self):
        depth = {"op": "du", "source": "site", "max_depth": 1, "human": True}
        self.assert_accepts(depth, "du -h --max-depth=1 site", "du -h -d 1 site")
        self.assert_rejects(depth, "du -h site", "du -sh site/*")
        every = {"op": "du", "source": "my photos", "all": True, "human": True}
        self.assert_accepts(every, "du -ah 'my photos'")
        self.assert_rejects(every, "du -h 'my photos'", "du -ak 'my photos'")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "du")


class TruncateTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "truncate", "target": "notes.txt", "size": 100}), "truncate -s 100 notes.txt")
        self.assert_invalid({"op": "truncate", "target": "a"}, {"op": "truncate", "target": "a", "size": -1})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "truncate", "target": "notes.txt", "size": 100}
        self.assert_accepts(intent, "truncate -s 100 notes.txt", "truncate --size=100 notes.txt",
                            "head -c 100 notes.txt > shrunk.tmp && mv shrunk.tmp notes.txt")
        self.assert_rejects(intent, "truncate -s 200 notes.txt", "head -c 100 notes.txt > notes.copy", "truncate -s 0 notes.txt")
        grow = {"op": "truncate", "target": "notes.txt", "size": 2000}
        self.assert_accepts(grow, "truncate -s 2000 notes.txt")
        self.assert_rejects(grow, "truncate -s 1000 notes.txt")

    def test_more_capabilities(self):
        grow = {"op": "truncate", "target": "notes.txt", "size": 2000}
        self.assert_accepts(grow, "truncate -s 2000 notes.txt", "cp notes.txt grown.tmp && truncate -s 2000 grown.tmp && mv grown.tmp notes.txt")
        self.assert_rejects(grow, "truncate -s 1000 notes.txt", "truncate -s 2000 notes.txt other.txt")
        empty = {"op": "truncate", "target": "notes.txt", "size": 0}
        self.assert_accepts(empty, "truncate -s 0 notes.txt", ": > notes.txt")
        self.assert_rejects(empty, "rm notes.txt", "truncate -s 1 notes.txt")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "truncate")


class InstallTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "install", "source": "tool.sh", "destination": "bin/tool.sh", "mode": "755"}),
                         "install -m 755 tool.sh bin/tool.sh")
        self.assert_invalid({"op": "install", "source": "a", "destination": "b"},
                            {"op": "install", "source": "a", "destination": "b", "mode": "999"},
                            {"op": "install", "source": "a", "destination": "a", "mode": "755"})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "install", "source": "tool.sh", "destination": "bin/tool.sh", "mode": "755"}
        self.assert_accepts(intent, "install -m 755 tool.sh bin/tool.sh", "cp tool.sh bin/tool.sh && chmod 755 bin/tool.sh")
        self.assert_rejects(intent, "cp tool.sh bin/tool.sh", "install -m 700 tool.sh bin/tool.sh", "mv tool.sh bin/tool.sh")

    def test_more_capabilities(self):
        dirs = {"op": "install", "source": "tool.sh", "destination": "opt/tools/bin/tool.sh", "mode": "755", "create_dirs": True}
        self.assertEqual(render(dirs), "install -D -m 755 tool.sh opt/tools/bin/tool.sh")
        self.assert_accepts(dirs, "install -D -m 755 tool.sh opt/tools/bin/tool.sh",
                            "mkdir -p opt/tools/bin && install -m 755 tool.sh opt/tools/bin/tool.sh")
        self.assert_rejects(dirs, "install -m 755 tool.sh opt/tools/bin/tool.sh", "install -D -m 644 tool.sh opt/tools/bin/tool.sh",
                            "mkdir -p opt/tools/bin && cp tool.sh opt/tools/bin/tool.sh")
        private = {"op": "install", "source": "app.conf", "destination": "backup/app.conf", "mode": "600"}
        self.assert_accepts(private, "install -m 600 app.conf backup/app.conf", "cp app.conf backup/app.conf && chmod 600 backup/app.conf")
        self.assert_rejects(private, "install -m 644 app.conf backup/app.conf", "install -m 755 app.conf backup/app.conf")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "install")


class MkfifoTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "mkfifo", "targets": ["events.fifo"]}), "mkfifo events.fifo")
        self.assert_invalid({"op": "mkfifo", "targets": []}, {"op": "mkfifo"})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "mkfifo", "targets": ["events.fifo"]}
        self.assert_accepts(intent, "mkfifo events.fifo", "mknod events.fifo p")
        self.assert_rejects(intent, "touch events.fifo", "mkfifo other.fifo")

    def test_more_capabilities(self):
        many = {"op": "mkfifo", "targets": ["-jobs.fifo", "results.fifo"]}
        self.assertEqual(render(many), "mkfifo -- -jobs.fifo results.fifo")
        self.assert_accepts(many, "mkfifo -- -jobs.fifo results.fifo", "mkfifo ./-jobs.fifo results.fifo")
        self.assert_rejects(many, "mkfifo -- -jobs.fifo", "touch ./-jobs.fifo results.fifo")
        private = {"op": "mkfifo", "targets": ["private.fifo"], "mode": "600"}
        self.assert_accepts(private, "mkfifo -m 600 private.fifo", "mkfifo private.fifo && chmod 600 private.fifo")
        self.assert_rejects(private, "mkfifo private.fifo", "mkfifo -m 666 private.fifo")
        self.assert_invalid({"op": "mkfifo", "targets": ["a"], "mode": "9"})

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "mkfifo")


class ShredTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "shred", "target": "secret.txt"}), "shred -u secret.txt")
        self.assert_invalid({"op": "shred"}, {"op": "shred", "target": "a", "remove": True})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "shred", "target": "secret.txt"}
        self.assert_accepts(intent, "shred -u secret.txt", "shred -n 1 -u secret.txt")
        self.assert_rejects(intent, "shred secret.txt", "true", "shred -u secret.txt keep/untouched.txt")

    def test_more_capabilities(self):
        once = {"op": "shred", "target": "session.key", "passes": 1}
        self.assertEqual(render(once), "shred -n 1 -u session.key")
        self.assert_accepts(once, "shred -n 1 -u session.key", "shred --iterations=1 --remove session.key")
        self.assert_rejects(once, "shred -n 1 session.key")
        quoted = {"op": "shred", "target": "private/old keys.txt"}
        self.assert_accepts(quoted, "shred -u 'private/old keys.txt'")
        self.assert_rejects(quoted, "shred -u private/old keys.txt")
        self.assert_invalid({"op": "shred", "target": "a", "passes": 0})

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "shred")


class FallocateTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "fallocate", "target": "blob.bin", "size": 10240}), "fallocate -l 10240 blob.bin")
        self.assert_invalid({"op": "fallocate", "target": "a"}, {"op": "fallocate", "target": "a", "size": 0})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "fallocate", "target": "blob.bin", "size": 10240}
        self.assert_accepts(intent, "fallocate -l 10240 blob.bin", "truncate -s 10240 blob.bin",
                            "head -c 10240 /dev/zero > blob.bin")
        self.assert_rejects(intent, "fallocate -l 1024 blob.bin", "touch blob.bin", "head -c 10240 /dev/urandom > blob.bin")

    def test_more_capabilities(self):
        kib = {"op": "fallocate", "target": "swap.img", "size": 64, "unit": "K"}
        self.assertEqual(render(kib), "fallocate -l 64K swap.img")
        self.assert_accepts(kib, "fallocate -l 64K swap.img", "fallocate -l 65536 swap.img", "fallocate --length 64KiB swap.img")
        self.assert_rejects(kib, "fallocate -l 64KB swap.img", "fallocate -l 64000 swap.img")
        mib = {"op": "fallocate", "target": "disk.img", "size": 2, "unit": "M"}
        self.assert_accepts(mib, "fallocate -l 2M disk.img", "truncate -s 2097152 disk.img")
        self.assert_rejects(mib, "fallocate -l 2000000 disk.img", "fallocate -l 2K disk.img")
        self.assert_invalid({"op": "fallocate", "target": "a", "size": 8, "unit": "M"}, {"op": "fallocate", "target": "a", "size": 1, "unit": "G"})

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "fallocate")


class GzipTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "gzip", "source": "notes.txt", "keep": True}), "gzip -k notes.txt")
        self.assertEqual(render({"op": "gzip", "source": "notes.txt"}), "gzip notes.txt")
        self.assert_invalid({"op": "gzip"}, {"op": "gzip", "source": "a", "keep": "yes"})

    def test_equivalent_and_wrong_commands(self):
        keep = {"op": "gzip", "source": "notes.txt", "keep": True}
        self.assert_accepts(keep, "gzip -k notes.txt", "gzip -c notes.txt > notes.txt.gz")
        self.assert_rejects(keep, "gzip notes.txt", "cp notes.txt notes.txt.gz", "touch notes.txt.gz", "gzip -k keep/untouched.txt")
        replace = {"op": "gzip", "source": "notes.txt"}
        self.assert_accepts(replace, "gzip notes.txt")
        self.assert_rejects(replace, "gzip -k notes.txt")

    def test_more_capabilities(self):
        replace = {"op": "gzip", "source": "client's report.txt"}
        self.assert_accepts(replace, "gzip \"client's report.txt\"", "gzip -f \"client's report.txt\"")
        self.assert_rejects(replace, "gzip -k \"client's report.txt\"", "gzip client's report.txt")
        best = {"op": "gzip", "source": "logs/app.log", "keep": True, "best": True}
        self.assertEqual(render(best), "gzip -k -9 logs/app.log")
        self.assert_accepts(best, "gzip -k -9 logs/app.log", "gzip --best --keep logs/app.log")
        self.assert_rejects(best, "gzip -9 logs/app.log", "gzip -k -9 logs")
        tree = {"op": "gzip", "source": "reports", "recursive": True}
        self.assertEqual(render(tree), "gzip -r reports")
        self.assert_accepts(tree, "gzip -r reports", "gzip reports/first.txt reports/nested/second.txt",
                            "find reports -type f -exec gzip {} +")
        self.assert_rejects(tree, "gzip -rk reports", "gzip reports/first.txt")

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "gzip")


class GunzipTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "gunzip", "source": "notes.txt.gz"}), "gunzip notes.txt.gz")
        self.assert_invalid({"op": "gunzip"}, {"op": "gunzip", "source": "notes.txt"})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "gunzip", "source": "notes.txt.gz"}
        self.assert_accepts(intent, "gunzip notes.txt.gz", "gzip -d notes.txt.gz",
                            "zcat notes.txt.gz > notes.txt && rm notes.txt.gz")
        self.assert_rejects(intent, "gunzip -k notes.txt.gz", "zcat notes.txt.gz", "zcat notes.txt.gz > notes.txt")

    def test_more_capabilities(self):
        keep = {"op": "gunzip", "source": "notes.txt.gz", "keep": True}
        self.assert_accepts(keep, "gunzip -k notes.txt.gz", "gzip -dk notes.txt.gz", "zcat notes.txt.gz > notes.txt")
        self.assert_rejects(keep, "gunzip notes.txt.gz")
        dash = {"op": "gunzip", "source": "-client's logs.txt.gz"}
        self.assert_accepts(dash, "gunzip -- \"-client's logs.txt.gz\"")
        self.assert_rejects(dash, "gunzip -k -- \"-client's logs.txt.gz\"")
        copy = {"op": "gunzip", "source": "data.csv.gz", "destination": "data-copy.csv"}
        self.assertEqual(render(copy), "gunzip -c data.csv.gz > data-copy.csv")
        self.assert_accepts(copy, "gunzip -c data.csv.gz > data-copy.csv", "zcat data.csv.gz > data-copy.csv")
        self.assert_rejects(copy, "gunzip -k data.csv.gz", "gunzip data.csv.gz")
        self.assert_invalid({"op": "gunzip", "source": "a.gz", "destination": "b", "keep": True})

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "gunzip")


class ZcatTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "zcat", "source": "notes.txt.gz"}), "zcat notes.txt.gz")
        self.assert_invalid({"op": "zcat"}, {"op": "zcat", "source": "notes.txt"})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "zcat", "source": "notes.txt.gz"}
        self.assert_accepts(intent, "zcat notes.txt.gz", "gunzip -c notes.txt.gz", "gzip -dc notes.txt.gz")
        self.assert_rejects(intent, "gunzip notes.txt.gz", "cat notes.txt.gz", "zcat notes.txt.gz | head -n 5")

    def test_more_capabilities(self):
        first = {"op": "zcat", "source": "events.log.gz", "lines": 5}
        self.assertEqual(render(first), "zcat events.log.gz | head -n 5")
        self.assert_accepts(first, "zcat events.log.gz | head -n 5", "gunzip -c events.log.gz | head -5")
        self.assert_rejects(first, "zcat events.log.gz | head -n 4", "zcat events.log.gz | tail -n 5", "zcat events.log.gz")
        nested = {"op": "zcat", "source": "logs/2024/app.log.gz"}
        self.assert_accepts(nested, "zcat logs/2024/app.log.gz")
        self.assert_rejects(nested, "zcat logs/app.log.gz")
        self.assert_invalid({"op": "zcat", "source": "a.gz", "lines": 0})

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "zcat")


class DdTests(FileCase):
    def test_render_and_validation(self):
        self.assertEqual(render({"op": "dd", "source": "in.bin", "destination": "out.bin", "block_size": 512, "count": 3}),
                         "dd if=in.bin of=out.bin bs=512 count=3 status=none")
        self.assert_invalid({"op": "dd", "source": "a", "destination": "b", "block_size": 512},
                            {"op": "dd", "source": "a", "destination": "b", "block_size": 0, "count": 1},
                            {"op": "dd", "source": "a", "destination": "b", "block_size": 4096, "count": 2},
                            {"op": "dd", "source": "a", "destination": "a", "block_size": 1, "count": 1})

    def test_equivalent_and_wrong_commands(self):
        intent = {"op": "dd", "source": "in.bin", "destination": "out.bin", "block_size": 512, "count": 3}
        self.assert_accepts(intent, "dd if=in.bin of=out.bin bs=512 count=3 status=none",
                            "dd if=in.bin of=out.bin bs=1536 count=1 status=none", "head -c 1536 in.bin > out.bin")
        self.assert_rejects(intent, "dd if=in.bin of=out.bin bs=512 count=3",
                            "dd if=in.bin of=out.bin bs=512 count=2 status=none", "cp in.bin out.bin")

    def test_more_capabilities(self):
        skip = {"op": "dd", "source": "disk image.bin", "destination": "part one.bin", "block_size": 512, "skip": 2, "count": 2}
        self.assertEqual(render(skip), "dd if='disk image.bin' of='part one.bin' bs=512 skip=2 count=2 status=none")
        self.assert_accepts(skip, "dd if='disk image.bin' of='part one.bin' bs=512 skip=2 count=2 status=none",
                            "tail -c +1025 'disk image.bin' | head -c 1024 > 'part one.bin'")
        self.assert_rejects(skip, "dd if='disk image.bin' of='part one.bin' bs=512 count=2 status=none",
                            "dd if='disk image.bin' of='part one.bin' bs=512 skip=1 count=2 status=none")
        patch = {"op": "dd", "source": "patch.bin", "destination": "disk.img", "block_size": 512, "seek": 2, "count": 1,
                 "notrunc": True}
        self.assertEqual(render(patch), "dd if=patch.bin of=disk.img bs=512 seek=2 count=1 conv=notrunc status=none")
        self.assert_accepts(patch, "dd if=patch.bin of=disk.img bs=512 seek=2 count=1 conv=notrunc status=none",
                            "dd if=patch.bin of=disk.img bs=1 seek=1024 count=512 conv=notrunc status=none")
        self.assert_rejects(patch, "dd if=patch.bin of=disk.img bs=512 seek=2 count=1 status=none",
                            "dd if=patch.bin of=disk.img bs=512 seek=1 count=1 conv=notrunc status=none")
        seek = {"op": "dd", "source": "in.bin", "destination": "padded.bin", "block_size": 512, "seek": 4, "count": 2}
        self.assert_accepts(seek, "dd if=in.bin of=padded.bin bs=512 seek=4 count=2 status=none",
                            "{ head -c 2048 /dev/zero; head -c 1024 in.bin; } > padded.bin")
        self.assert_rejects(seek, "dd if=in.bin of=padded.bin bs=512 count=2 status=none")
        self.assert_invalid({"op": "dd", "source": "a", "destination": "b", "block_size": 512, "count": 9},
                            {"op": "dd", "source": "a", "destination": "b", "block_size": 512, "count": 1, "skip": 8},
                            {"op": "dd", "source": "/dev/zero", "destination": "b", "block_size": 512, "count": 1})

    def test_catalog_scenarios_pass(self):
        self.assert_catalog_passes("filesystem", "dd")


if __name__ == "__main__":
    unittest.main()
