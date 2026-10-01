# Milestone 2: untouched Qwen3 0.6B comparison

Run date: 2026-09-28. Documented initially that day; moved into the project notebook on 2026-10-01. Both checkpoints ran in float16 on an RTX 2060, with greedy decoding and a 32-token output limit. The base checkpoint used `Request: ...\nCommand:`. The instruction-tuned checkpoint used Qwen's chat template with `enable_thinking=False` and the system instruction in `baseline.py`. The table records the first output line; the script also prints full continuations.

| Request | Base, raw prompt | Instruct, chat prompt | Expected behavior |
| --- | --- | --- | --- |
| enter the root directory | `cd` | `root-directory` | `cd /` |
| list all files including hidden ones | `ls -a` | `ls -a` | `ls -a` or equivalent |
| show my current directory | `cd` | `cd /root` | `pwd` |
| create a directory called projects | `mkdir projects` | `mkdir projects` | `mkdir projects` |
| go to my home directory | `cd ~` | `cd ~` | `cd ~` or `cd` |
| show the first five lines of README.md | `git log --pretty=oneline --abbrev-commit --all` | `show the first five lines of README.md` | `head -n 5 README.md` |
| count the lines in report.txt | `count report.txt` | `count lines in report.txt` | `wc -l report.txt` |
| copy a.txt to b.txt | `cp a.txt b.txt` | `cp a.txt b.txt` | `cp a.txt b.txt` |
| rename old.txt to new.txt | `mv old.txt new.txt` | `rename old.txt to new.txt` | `mv old.txt new.txt` |
| delete the file old.log | `rm old.log` | `delete old.log` | `rm old.log` |
| find all .log files under the current directory | `find . -name "*.log"` | `find .log` | `find . -type f -name '*.log'` or equivalent |
| search recursively for TODO in the current directory | `find . -type f -name "*.java" -exec grep -l "TODO" {} \\;` | `search TODO in current directory` | `grep -R TODO .` or equivalent |

Manual strict first-line count: Base 6/12; instruction-tuned chat 4/12. The base model's `find` output is partial credit because it can also match directories named `*.log`. This tiny hand-picked test is diagnostic, not a model benchmark. The instruction-tuned model was also run on the original four prompts with the raw `Request/Command` format and got 0/4 correct first lines.

The instruction-tuned model's chat output was generally a single line, while the base model frequently continued with extra text after a newline. Neither checkpoint is ready to translate arbitrary requests reliably without task-specific tuning. Peak PyTorch allocations were 1.12 GiB for Base and 1.13 GiB for the chat run.

## Limitations and provisional decision

The raw-prompt check on the original four requests compares checkpoints under the same text format. The twelve-request table changes both the checkpoint and the prompt format, including an added system instruction. It therefore compares these particular configurations, not the effect of instruction tuning alone.

Qwen recommends sampling settings for non-thinking use; we instead used greedy decoding to match the intended deterministic translator baseline. These results do not cover all recommended operating settings. Model repository revisions were not explicitly pinned in the script. Dependencies are locked, but an exact replay of the model download is not guaranteed by the recorded commands.

The outputs were inspected manually and were never executed. Whole-response format compliance was not scored, and the raw stdout was not saved to a separate results file. The recorded first-line table preserves the observations made during the session.

We provisionally kept Base as the training candidate because it already supports the chosen plain prompt and performed better in this small run. This does not establish which checkpoint will perform better after task-specific fine-tuning.

To repeat using the current twelve-request script, first follow the [environment setup](wsl-cuda-environment-setup.md), then run:

```bash
uv run python baseline.py --model Qwen/Qwen3-0.6B-Base
uv run python baseline.py --model Qwen/Qwen3-0.6B
uv run python baseline.py --model Qwen/Qwen3-0.6B --prompt-style chat
```

The second command now runs all twelve requests; the historical raw-prompt instruction-tuned check used only the original four.

Reference: [Qwen3-0.6B model card and non-thinking guidance](https://huggingface.co/Qwen/Qwen3-0.6B).
