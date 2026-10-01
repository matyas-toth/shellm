# Translator task contract: pilot v1

Established: 2026-10-01. This is the task contract for the first functional evaluation milestone.

## Interface and environment

Input is one standalone English request. The model receives:

```text
Request: <request>
Command:
```

Output is one Bash command line, with no Markdown or explanation. A command line may contain a pipeline. The reference environment is Linux with Bash and GNU utilities, initially in `/workspace`, with `HOME=/home/shellm`. Paths without a leading slash are relative to the current directory. Names, capitalization, spaces, and literal patterns must be preserved.

Decoding stops at EOS or the first newline, with a 64-token cap in the evaluation runner. Newline stopping is an inference policy; it does not demonstrate that the model learned to emit EOS. A blank first line fails. The evaluator records the full decoded continuation, extracts the first line, and scores output shape separately from its behavior.

## Initial command families

The suite has eight cases per family, for 112 total requests. Families describe the requested capability; predictions may use equivalent alternative commands.

| Family | Pilot coverage |
| --- | --- |
| `pwd` | Absolute working directory; varied and informal phrasing |
| `cd` | Root, home, parent, subdirectories, absolute paths, quoted names |
| `ls` | Ordinary and hidden entries, long listings, specified directories |
| `mkdir` | New directories, missing parents, multiple names, mode 700, leading dashes |
| `touch` | New empty files, nested destinations, multiple files, quoted names |
| `cp` | File copies, directory copies, multiple sources, quoted paths |
| `mv` | Renaming, moving into directories, multiple sources, quoted paths |
| `rm` | Specific files, multiple files, recursive removal of a specified directory |
| `cat` | Complete file contents, multiple files in an explicit order |
| `head` | First N lines or bytes |
| `tail` | Last N lines or bytes |
| `wc` | Line, word, and byte counts |
| `grep` | Literal matches, case handling, line numbers, inverse matches, counts, recursive file paths |
| `find` | Regular files versus directories, extensions, depth, empty files, combined extension/size filters |

The labels in `eval/cases.jsonl` include argument variation, options, composition, informal phrasing, and quoted arguments. These are coverage labels, not evidence of generalization after training. No training split exists yet.

## Scope boundaries

The pilot uses explicit requests with known targets. Clarification behavior for ambiguous or underspecified requests remains an open product decision. Package management, networking, privileged administration, permissions beyond the covered directory mode, interactive commands, background jobs, and arbitrary scripts are outside this pilot.

Fixtures include filenames with spaces, apostrophes, and leading dashes. Embedded newlines in filenames are not covered. Creating empty files is covered; updating timestamps on existing files is not.

## Definition of success

A prediction passes functionality only if it behaves like the checked reference on both fixture variants: successful execution, correct standard output, matching final working directory, and matching observable filesystem state. A usable prediction additionally obeys the output format.

Passing two fixtures establishes behavior in those scenarios. It is not a proof of equivalence for all possible filesystems, permission states, or shell environments. For example, unnecessary `rm -rf` flags can behave the same as `rm` on these fixtures; a separate command-policy metric would be needed to penalize them.

These cases are a development evaluation set. Keep their exact requests out of training data. Create a separate final test set before treating results as a published generalization benchmark.
