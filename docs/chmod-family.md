# chmod command family

Completed: 2026-10-02 (Europe/Budapest). Not yet used in a training run.

## What we added

A fifteenth family, `chmod`, covering octal modes, symbolic modes, recursion, and directory targets. Rare features are out of scope: `X`, `--reference`, `-v`/`-c`/`-f`, setuid/setgid/sticky bits, and symbolic clauses with no `who` (their meaning depends on umask).

| File | Change |
| --- | --- |
| `shellm_data/intents.py` | `chmod` schema, renderer, fixture generator, effect checker, symbolic-mode arithmetic |
| `data/shell_translation/catalogs/pilot-v1/filesystem/chmod.json` | 36 scenarios (30 train, 6 validation), 4 paraphrases each |
| `tests/test_chmod_intent.py` | Render and validation tests, plus Docker tests that equivalent commands pass and wrong ones fail |

### Intent shape

`targets` is required, plus exactly one of:

- `mode`: three octal digits, for example `"750"`.
- `changes`: a list of `{"who", "op", "perms"}`. `who` is `u`, `g`, `o`, a combination such as `go`, or `a`. `op` is `+`, `-`, or `=`. `perms` is a subset of `rwx` and may be empty only with `=`.

Optional: `recursive` (`-R`) and `directory_target` (the target is a directory and only the directory itself changes). They are mutually exclusive. Example: `{"who": "go", "op": "-", "perms": "w"}` renders as `go-w`; several changes join with commas, as in `u=rw,g=r,o=`.

The oracle computes the expected bits per entry from its starting mode (files 644, directories 755), so `g+w` recursively must give 775 on directories and 664 on files. A flat `chmod -R 775` is rejected. Recursive intents may not clear owner read or execute (`u-x`, `a=w`), because real `chmod -R` then cannot descend into the directory and exits with an error.

## Coverage

- 21 octal scenarios: modes 400, 600, 644, 700, 750, 755, 775; single and multiple files, recursive directories, and one directory-itself case.
- 15 symbolic scenarios: single-clause (`u+x`, `go-w`, `a=r`, `g+w`, `o-rwx`, `a+x`), multi-clause (`u=rw,g=r,o=`, twice), recursive (`g+w`, `o-rwx`, `g+w`), multiple targets (`u+x`, twice), and one directory-itself case (`g+w`).
- Argument edge cases: spaces, an apostrophe, leading dashes.
- Validation scenarios use the reserved `tundra` and `zephyr` names and include symbolic, multi-clause, and recursive cases.

Chmod now has 144 examples rather than the 80 per family elsewhere, so the earlier "80 per family" balance no longer holds.

## Decision: extend pilot-v1 in place

We edit `pilot-v1` instead of creating `pilot-v2`, agreed with Reigniteh: Git keeps the history, and the trainer loads exactly one release (`dataset_release` in the config) without merging releases. The release was deleted and rebuilt, since the compiler refuses to overwrite.

Consequences: `pilot-v1` now has 1,264 examples (1,128 train / 136 validation), 316 groups, 297 unique commands. The dataset SHA-256 changed from `57653a79...f1594` to `2407ee3d...78fa`. The existing 14 family shards are byte-identical. The first LoRA run in [first-lora-training-experiment.md](first-lora-training-experiment.md) used the earlier 1,008/112 data, so its numbers do not describe the current release. Figures in older docs are historical.

## Verification

```bash
python3 -m shellm_data build --release pilot-v1
python3 -m shellm_data validate --release pilot-v1
python3 -m shellm_data build --release pilot-v1 --check
python -m unittest discover -s tests
```

All 316 groups passed on two fixtures each (632 executions). `--check` passed and request overlap with both evaluation suites is 0. The full suite passed with 41 tests, including the Qwen tokenizer prompt-boundary, EOS, and loss-masking checks on the new examples and 12 chmod tests (the Docker ones cover unquoted names with spaces, a leading-dash target without `--`, and changing only one of two targets, which must all fail). Those ran in a CPU-only environment (uv venv with CPU `torch` 2.14.1 and `transformers` 4.57.6) on a machine without an NVIDIA GPU. This is a test environment only, not a training setup.

## Limits and next step

Paraphrases follow shared templates, so linguistic variety is modest. ShellBench Extra v1's `permissions` family phrases requests more loosely ("accessible only to its owner") and mixes in other commands (`touch ... && chmod`, `stat`, `cp ... && chmod`), which this family does not teach. Next: train on the rebuilt `pilot-v1` (needs a CUDA GPU) and compare on that `permissions` family.
