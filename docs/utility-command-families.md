# Utility command families (tier A)

Completed: 2026-10-02, quality pass 2026-10-03 (Europe/Budapest). Not yet used in a training run.

## What we added

Specs for 61 commands from the 10/10 cross-distro intersection ([triage](../data/distro_cmds/triage_10of10.md), tier A). 59 of them have a catalog in `pilot-v1` with 5 validated scenarios of 4 paraphrases each: `-01` to `-04` train, `-05` validation. `link` and `unlink` keep their Specs and unit tests but have no catalog, because every natural request for them belongs to `ln` and `rm`.

| Module | Commands |
| --- | --- |
| `shellm_data/utilities/text.py` (26) | sort, awk, sed, uniq, cut, tr, paste, nl, tac, rev, fold, expand, unexpand, comm, od, split, tee, xargs, iconv, base64, md5sum, sha1sum, sha256sum, sha512sum, cksum, sum |
| `shellm_data/utilities/files.py` (19) | ln, link, unlink, rmdir, readlink, realpath, basename, dirname, stat, du, truncate, install, mkfifo, shred, fallocate, gzip, gunzip, zcat, dd |
| `shellm_data/utilities/shellutils.py` (16) | echo, printf, seq, expr, factor, true, false, test, yes, sleep, timeout, env, printenv, whoami, id, groups |

Catalogs are in `catalogs/pilot-v1/text/`, `filesystem/`, and the `shell-utils/` topic folder.

## How it works

`shellm_data/utilities/base.py` defines a `Spec` per command: typed `fields`, a `required` set, and `render`, `fixture`, `check` functions, plus an optional expected `returncode`. `intents.py` merges all specs into its schema, validator, renderer, fixture generator, and oracle, so adding a command does not mean editing the large `if` chains.

Each oracle computes the expected stdout and filesystem effect in Python without running the command. The authors probed or fuzzed the oracles against the real tools in the container.

## Quality pass (2026-10-03)

A review of all 341 new groups found that the first version taught little. These changes fix it:

- **Natural requests.** Many requests named the program or dictated the command ("run printf with the format …", "using du", "with the test command"). Requests now describe the goal. Format and algorithm names (gzip, base64, MD5, SHA-256, ISO-8859-1) are allowed, and wrappers (`env`, `timeout`, `xargs`) may name the command they run.
- **Real paraphrases.** The four paraphrases used to differ only by their first verb. Each scenario now uses at least three sentence structures (imperative, question, "I want …"), and each validation scenario uses sentence templates that no training scenario of its family uses.
- **One canonical command per intent.** Decisions:
  - Fields split on a single-character delimiter go to `cut`. `awk` covers whitespace columns, filtering by a field value, and sums.
  - A link's raw target goes to `readlink`; the fully resolved path goes to `realpath`.
  - Byte counts stay with `wc`. `stat` covers metadata: permissions, type, owner, modification time.
  - `du` means disk usage. On the container's tmpfs, each regular file uses whole 4 KiB pages and directories use none.
  - `fallocate` preallocates, `truncate` resizes, and `dd` copies blocks.
  - `zcat` prints decompressed contents; `gunzip` writes files.
  - `whoami` gives the user name (no `id -un`). `echo` prints plain lines; `printf` handles formatting (one per line, tabs, `%03d`, `%.2f`).
  - `printenv` reads one existing variable. `env` lists everything or runs a command with a changed environment.
  - Hard links use `ln`.
- **Contrived scenarios removed.** `:`, `/bin/true`, `(exit 1)`, ignored arguments, `whoami | rev`-style pipelines and "so that it gets killed" requests are gone. `true`, `false` and `whoami` follow the `pwd` precedent: five phrasing groups for the same command.
- **Rendering.** `sed` programs are always single-quoted. All families, including the original ones and `chmod`, now share one quoting helper (`quote` in `base.py`). It double-quotes a value containing an apostrophe (`touch "client's notes.txt"`), as both evaluation suites' references do, instead of `'client'"'"'s notes.txt'`. This changed the labels of the few original-family scenarios with apostrophes. The first LoRA report lists that escaped style among its exact-match differences.
- **Linter.** `tools/lint_requests.py` enforces the request rules: no program names, no cross-family skeleton conflicts, no validation template reuse, and no first-word-only paraphrases. All 331 linted groups (the new families and `chmod`) pass. The original 14 families are not linted by default; they still use first-word-only paraphrases.

## Shared infrastructure changes

These touch files outside the new package:

| File | Change |
| --- | --- |
| `shellbench/worker.py` | Optional `binary_files` in a fixture (base64), needed for `gunzip` and `zcat` |
| `shellbench/oracle.py` | `initial_state` includes `binary_files` |
| `shellm_data/intents.py` | Registry hooks, `api.binary`, `api.symlink`, per-command expected exit status, shared quoting |

The evaluation image changed with the worker, so it was rebuilt: the image ID moved from `sha256:ed08010b…` to `sha256:917688aa…`. The new keys are optional and the existing ShellBench tests pass, but the recorded image ID of earlier evaluation reports no longer matches new runs. Replaying the Base predictions on the new image (30/112 expected) would confirm that the original benchmark is unaffected; that has not been run.

## Limits

- Weak oracle distinctions:
  - `sleep` durations are not measured.
  - `id -u`, `id -g` and `id -G` all print 1000 for the container user.
  - The owner from `stat -c %U` equals `whoami`.
  - A hard link cannot be told from a copy.
  - The `gzip` output bytes cannot be reproduced in Python. The oracle requires a plausible regular file and adopts its hash; everything else is checked strictly.
- Environment-specific:
  - The `du` model holds only on tmpfs.
  - `whoami`, `id`, `groups`, `printenv` and `env` hardcode the container's user and environment.
  - Several flags are GNU-only (`du --max-depth`, `base64 -w`, `env -u`), which matches the GNU task contract but not every distro's version of the command.
- Scope: `shred` only removes (`-u`). `dd` needs `status=none` because its statistics go to stderr. `xargs` covers deleting, concatenating, creating and backing up listed files. `iconv` supports UTF-8, ISO-8859-1 and UTF-16LE. `sed`, `awk`, `cut` and `tr` use plain patterns, one-character delimiters and `a-z` style ranges. Hash `-c` checks cover only the all-OK case.
- Names starting with a dash use distinct stems (`-spaced.txt`), because request normalization drops punctuation and would otherwise collide with `spaced.txt`.
- Each family has a single validation scenario, and the paraphrases were authored by the same people who designed the intents, so a separate blinded test set is still needed for generalization claims.

## Verification

```bash
python3 -m shellm_data build --release pilot-v1
python3 -m shellm_data validate --release pilot-v1
python3 -m shellm_data build --release pilot-v1 --check
python3 tools/lint_requests.py
python -m unittest discover -s tests
```

`pilot-v1` now has 2,444 examples (2,072 train / 372 validation) across 611 groups and 577 unique commands. The dataset SHA-256 is `efa33aaf…d073` (it was `2407ee3d…78fa` before the 61 families were added). All 611 groups passed on two fixtures (1,222 executions), `--check` passed, request overlap with both evaluation suites is 0, and the linter reports 0 problems. The full suite passed with 174 tests (562 s).

## Next step

Train on the rebuilt `pilot-v1` (needs a CUDA GPU) and compare. Tier B and C commands remain out of scope.
