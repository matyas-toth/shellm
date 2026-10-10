# Project goals and roadmap

Documented: 2026-10-01. Initial discussion and experiments: 2026-09-28.

## Intended product

Translate short English requests into Linux shell commands. For example:

```text
Input: enter the root directory
Output: cd /
```

The project has two learning goals: understand model training and build inference software, eventually including WebGPU kernels that run the model in a browser. We start from a pretrained model so the experiments can focus on adapting existing language knowledge to this task.

The initial candidate is `Qwen/Qwen3-0.6B-Base`. The first supervised LoRA experiment has now run on the RTX 2060; QLoRA remains an optional future experiment. The intended interface returns a command as text. Executing that command is a separate concern. In particular, `cd` changes the directory of the shell that executes it.

## Completed work

1. Inspected the initially empty repository and checked WSL/GPU availability.
2. Created a minimal uv project with CUDA PyTorch and Transformers.
3. Loaded the Base checkpoint in float16 on the RTX 2060 and generated commands.
4. Compared the Base and instruction-tuned checkpoints on twelve fixed requests.
5. Discussed smaller pretrained models as future experiments.
6. Created this documentation notebook and repository instructions for keeping it updated.
7. On 2026-10-01, established the task contract, built a 112-case Docker functional evaluation suite, validated its references and scoring behavior, and recorded a reproducible Base-model baseline.
8. On 2026-10-01, built a versioned dataset with 1,008 training and 112 validation examples, validated 280 command scenarios on two fixtures, and completed a three-epoch LoRA training run. Checkpoint evaluations and report history preserve progress for future charts.
9. On 2026-10-02, added the separate 300-case ShellBench Extra v1 progress benchmark; it remains outside training and validation.
10. On 2026-10-03, completed a fresh expanded-data adapter using 2,072 training examples: 84.8% on v1 and 25.7% on Extra.
11. On 2026-10-10, prepared and validated pilot-v2, then trained a fresh adapter on its 18,392 training examples for three epochs. Functional scores reached 92.9% on v1 and 34.3% on Extra; reports, regressions and Base comparison charts are preserved in [the experiment notebook](pilot-v2-fresh-lora-experiment.md). Stronger independent composition validation remains proposed work.

## Proposed progression

| Milestone | Result we want |
| --- | --- |
| Define scope and build evaluation cases (completed) | A task contract, 112 checked cases, Docker runner, and baseline |
| Build a small validated training dataset (completed) | 1,008 training examples plus 112 validation examples, editable catalogs, and checked JSONL releases |
| Run a first LoRA training experiment (completed) | Three epoch adapters; functional accuracy improved from 26.8% to 80.4% |
| Improve coverage and generalization | Data changes guided by failures, including quoting, composition, and unusual wording |
| Study inference and tokenization | Understand the model's tensors and tokenizer; reproduce reference outputs |
| Quantize and build browser inference | Smaller weights and WebGPU operations checked against a reference implementation |
| Prepare distribution | Code and documentation on GitHub; model artifacts and model card on Hugging Face; a browser demo |

These are milestone boundaries, not a commitment to implement everything in one turn. The user's preference is to stop after each unit of progress and discuss it.

## Dataset ideas carried forward

Construct commands from checked templates, then write diverse English requests for them. Cover simple commands, paraphrases, arguments, compositions, informal wording, and eventually ambiguous requests. Keep related paraphrases together when splitting data and use dedicated argument and composition holdouts.

A valid command does not guarantee that a generated paraphrase describes it correctly. Both the command and the meaning of its English request need review. Docker functional evaluation and the small synthetic pilot are implemented. Broader linguistic diversity, stronger composition holdouts, and a separate blinded test set remain future work.
