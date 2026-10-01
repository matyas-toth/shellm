# Functional baseline results: Qwen3 0.6B Base

Run date: 2026-10-01. This report records the untouched model before fine-tuning.

## Configuration and artifacts

- Model: `Qwen/Qwen3-0.6B-Base`.
- Pinned model commit: `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`.
- Hardware: RTX 2060 in WSL, model loaded in float16.
- Prompt: `Request: <request>\nCommand:`; greedy decoding, EOS/newline stopping, 64-token cap.
- Suite: 112 cases, each checked on two fixture variants.
- Artifacts: [predictions](../reports/base-functional-baseline/predictions.jsonl), [generation metadata](../reports/base-functional-baseline/generation-metadata.json), [evaluation results](../reports/base-functional-baseline/evaluation.json).

Generation took about 127 seconds excluding model loading. Peak PyTorch GPU tensor allocation was approximately 1.15 GiB. This was not a controlled inference performance benchmark.

## Results

| Metric | Passed | Rate |
| --- | --- | --- |
| Functional correctness on both fixtures | 30 / 112 | 26.8% |
| Usable: functional correctness plus format | 30 / 112 | 26.8% |
| Exact command match | 14 / 112 | 12.5% |
| Bash syntax accepted | 108 / 112 | 96.4% |
| Single-line format accepted | 111 / 112 | 99.1% |

The output-format result includes inference-time newline stopping. It should not be attributed to learned EOS behavior. Syntax validity also does not mean that the command performs the requested task.

Sixteen passing outputs differed from the reference string. For example, the model generated `cat README.md | tail -n 5` for the last-five-lines request and `cd` for the home-directory request. Both behaved correctly on the two fixtures.

## Results by family

| Family | Functional passes out of 8 |
| --- | --- |
| `pwd` | 2 |
| `cd` | 3 |
| `ls` | 1 |
| `mkdir` | 2 |
| `touch` | 1 |
| `cp` | 2 |
| `mv` | 3 |
| `rm` | 3 |
| `cat` | 1 |
| `head` | 2 |
| `tail` | 5 |
| `wc` | 2 |
| `grep` | 2 |
| `find` | 1 |

Examples of failures include `ls` for a request asking for the current path and `git checkout -b /workspace/src` for a directory-change request. These are stronger evidence of task failure than differences in command spelling.

The results cannot be directly compared with the earlier twelve-request experiment: the requests, stopping policy, token cap, checks, and explicitly resolved model revision differ. This run establishes a reproducible development baseline for subsequent training.

The generation metadata retains the suite hash from prediction generation. Two long-listing comparison tags were subsequently corrected after a repeat test exposed timestamp sensitivity; requests and references stayed identical. The saved predictions were rescored with the final comparator, whose suite and code hashes are in `evaluation.json`.

## Next milestone

Build a small validated training pilot around the same capability taxonomy while excluding evaluation requests. Include varied wording and carefully quoted arguments, then run a first LoRA training experiment and score its saved predictions with this same evaluator.

Keep these cases for development feedback. A separate untouched test set and stronger argument/composition splits are still needed before making public claims about generalization.
