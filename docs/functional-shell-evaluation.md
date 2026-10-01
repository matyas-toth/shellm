# Functional shell evaluation with Docker

Implemented and verified: 2026-10-01.

## What we built

`eval/cases.jsonl` contains 112 individually authored requests and reference commands across 14 families. `shellbench/fixtures.py` creates two deterministic filesystem variants. The variants change file contents and counts, so hardcoded output that succeeds on one fixture can fail on the other.

Fixtures include hidden entries, nested files, a symlink, empty files, Unicode text, quoted names, literal-pattern decoys, and directories named `directory.log` and `directory.py`. These last directories catch `find` commands that forget to restrict results to regular files. All referenced paths exist where appropriate, and file-creation destinations initially do not.

## Reference validation

References run in a trusted batch container. Before accepting them, the runner checks syntax, exit status, timeout and output limits, then validates each result against independent Python expectations in `shellbench/oracle.py`.

Those expectations describe intended file creation, copies, moves, deletion, directory changes, text slices, counts, searches, and listing contents. They do not execute or parse the reference shell commands to manufacture their expected answers. This helps catch a reference that is runnable but describes the wrong task.

All 112 references passed these checks on both variants: 224 validated reference executions. The suite was authored and checked during this project, rather than imported from a published benchmark. Human review and broader fixtures can strengthen it further.

## Candidate execution and isolation

Each prediction gets a fresh disposable container, independently of reference execution. Its two variants are initialized separately inside that container. The runner compares captured observations on the host; the generated command never executes in the host shell.

Containers run as uid 1000 with a read-only root filesystem, no network, no added host mounts or Docker socket, all capabilities dropped, and no privilege escalation. Writable fixture directories and temporary files use bounded tmpfs mounts. Each container is limited to one CPU, 128 MiB of memory, and 64 processes. Commands have a three-second deadline and a 64 KiB captured-output limit. Remaining subprocesses are terminated after command completion.

The Dockerfile pins the base image digest. Evaluation records the built image ID. Reference caches are keyed by image, cases, and fixtures, and independently validated again when reused. Containers are removed after use; the image and ignored reference cache are retained for future runs.

This is a local development evaluator, not a hardened service for deliberately hostile code.

## What is compared

| Observation | Check |
| --- | --- |
| Bash syntax | `bash -n` in the container |
| Exit status | Must match the successful reference |
| Working directory | Captured within the shell that executed the command, including `cd` |
| Filesystem | Paths, object types, permissions, file sizes, SHA-256 contents, and symlink targets under `/workspace` and the home directory |
| Standard output | Exact bytes-as-decoded-text, sorted output lines, long-listing metadata, or a single numeric count according to the case |
| Standard error | Must match the reference |
| Format | Nonempty single line, no code fence or enclosing Markdown backticks |

For a numeric count, both `wc -l report.txt` and `cat report.txt | wc -l` can pass despite different output labels. Line comparisons preserve duplicate counts. Filesystem checks also apply to read-only tasks, so `pwd; rm notes.txt` fails even though it prints the correct directory.

A repeat integration run exposed nondeterministic timestamps in `ls -la`, including the parent directory and symlink. Long-listing checks now compare filenames and symlink targets, type/permissions, link counts, owner/group labels, and sizes while ignoring timestamps and the block-total line. A regression check verifies that time differences pass while size or permission differences fail.

`functional_ok` requires both variants to pass. `usable` requires functionality and format together. Exact command match is recorded as a diagnostic metric and does not decide functional success.

## Repeat the milestone

Use the [WSL environment](wsl-cuda-environment-setup.md). Docker Desktop must be running with its Linux engine. On this machine WSL integration was unavailable, so the runner falls back to the Windows `docker.exe` visible in WSL. Build context is streamed over stdin, avoiding host-path translation or bind mounts.

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv run python -m shellbench build
uv run python -m shellbench validate
uv run python -m unittest discover -s tests -v
uv run python -m shellbench generate
uv run python -m shellbench evaluate \
  --predictions reports/base-functional-baseline/predictions.jsonl
```

`generate` resolves the model revision to a commit before loading. For an exact repeat of the recorded run, pass `--revision da87bfb608c14b7cf20ba1ce41287e8de496c0cd`. Use a new `--output` directory to preserve the original predictions, then supply that file and a new evaluation `--output` path when scoring.

Model predictions, generation settings, suite hash, evaluation-code hash, and detailed per-case checks are retained under `reports/`. Scoring existing predictions needs Docker and standard Python, but no GPU or new model download.

## Verification and limits

Integration checks accept an alternative command for each of the 14 families and reject a deliberately wrong command for each. Additional checks exercise incorrect quoting, extra deletions, invalid syntax, timeouts, read-only system files, varying fixture counts, output format, and count/line/listing equivalence.

Final verification passed all 12 test methods, including the 28 family-level alternative/wrong-command subcases. Rescoring after the timestamp fix kept the baseline at 30/112 functional passes. No evaluation containers remained running at completion.

The evaluator does not measure mtimes, ownership, ACLs, xattrs, or writes to scratch `/tmp`. Accordingly, cases do not request timestamp or ownership preservation. Output equivalence is intentionally constrained: some correct variants, such as alternative path formatting or human-readable long listings, may fail the current stdout comparator. Fixture behavior should be broadened when concrete model outputs reveal such gaps.

ShellCheck has not been installed or integrated. Syntax validation and functional execution are implemented; ShellCheck can be added later as another diagnostic.

References: [Docker run options](https://docs.docker.com/reference/cli/docker/container/run), [Docker tmpfs mounts](https://docs.docker.com/engine/storage/tmpfs).
