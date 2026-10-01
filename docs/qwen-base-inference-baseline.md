# Qwen Base inference baseline

Experiment date: 2026-09-28. Documented: 2026-10-01.

## Purpose and method

Load the untouched `Qwen/Qwen3-0.6B-Base` checkpoint and establish that GPU generation works before adding training code. This is a pretrained text-completion model. Our proposed task prefix is:

```text
Request: enter the root directory
Command:
```

`baseline.py` loads the tokenizer and causal language model through Transformers, moves the model to CUDA in float16, calls `model.eval()`, and generates under `torch.inference_mode()`. Decoding is greedy, with a maximum of 32 new tokens. No chat template is used for this baseline.

The script prints both the raw continuation and its first line. First-line extraction is postprocessing: generation itself can continue beyond a newline. The tokenizer's EOS token is used for padding; this inference experiment does not add training examples or train EOS behavior.

## Initial four requests

| Request | First generated line | Assessment |
| --- | --- | --- |
| enter the root directory | `cd` | Wrong; bare `cd` goes to the user's home directory |
| list all files including hidden ones | `ls -a` | Correct for the request |
| show my current directory | `cd` | Wrong; expected `pwd` |
| create a directory called projects | `mkdir projects` | Correct |

The model often continued after its first line. For example, after `mkdir projects` it invented additional `Request:` and `Command:` examples. This shows why command correctness and output-format compliance need separate measurements.

Peak PyTorch GPU allocation was 1.12 GiB. This measurement covers tensors tracked by PyTorch, not all GPU memory used by the CUDA context, other libraries, Windows, or other applications.

## Files and verification

- `baseline.py`: reusable inference script, later extended with chat prompting and twelve requests.
- `pyproject.toml` and `uv.lock`: dependency configuration and resolved versions.
- `.gitignore`: keeps virtual environments, caches, generated weights, and checkpoints out of Git.

The initial run succeeded. A deprecation warning about `torch_dtype` was corrected by using `dtype`, and the updated script was rerun successfully. The full raw stdout was observed during the session but was not archived as a separate machine-readable artifact.

The script never executed generated commands. These assessments are manual inspections, not functional test results. No task-specific model training has occurred.

Reference: [Qwen3-0.6B-Base model card](https://huggingface.co/Qwen/Qwen3-0.6B-Base).
