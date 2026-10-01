# First LoRA training experiment

Date: 2026-10-01 (Europe/Budapest). Run ID: `2026-10-01-lora-pilot-v1`.

## Purpose

Teach the pretrained Base model our English-to-command interface using the validated pilot dataset, then measure actual command behavior on the preserved 112-case development suite. This is supervised fine-tuning: the examples supply the desired command. LoRA is the method for adapting weights using small trainable matrices while keeping the original weights frozen.

## Configuration

Configuration: `configs/training/lora-pilot-v1.json`.

| Setting | Value |
| --- | --- |
| Base model | `Qwen/Qwen3-0.6B-Base` |
| Base revision | `da87bfb608c14b7cf20ba1ce41287e8de496c0cd` |
| Dataset | `pilot-v1`: 1,008 training / 112 validation examples |
| Epochs | 3 |
| LoRA rank / alpha / dropout | 8 / 16 / 0.05 |
| LoRA targets | Attention q/k/v/o and MLP gate/up/down projections |
| Trainable parameters | 5,046,272 out of 601,096,192 including adapters (0.84%) |
| Precision | Frozen base FP16; trainable adapters and AdamW states FP32; FP16 autocast |
| Microbatch / effective batch | 2 / 16 examples |
| Gradient accumulation | Eight microbatches per update |
| Learning rate | 0.0002 with 10 warmup steps and cosine decay |
| Gradient clipping / weight decay | 1.0 / 0 |
| Maximum sequence length | 128; observed maximum 50 |
| Seed | 42 |

Ordinary LoRA fit comfortably on the RTX 2060, so we did not need QLoRA or bitsandbytes for this experiment. PEFT and Accelerate were added to the uv project; their installed versions are recorded with the experiment. The custom, compact PyTorch training loop makes loss masking, gradient accumulation, and optimizer updates directly readable. TRL, datasets, and TensorBoard are not required by this pilot.

## What the trainer does

`shellm_training/data.py` tokenizes the request prefix and command, appends EOS, masks prompt/padding labels with `-100`, and rejects truncation. `shellm_training/__main__.py` checks release hashes and functional validation, loads the pinned model, installs LoRA, enables gradient checkpointing, and optimizes only trainable parameters. Accumulated gradients use the number of supervised command tokens, so unequal command lengths do not incorrectly weight microbatches equally.

The loop records each update attempt, detects FP16 overflow skips, measures held-out completion loss before training and after each epoch, saves adapters/tokenizers, and verifies that adapter weights actually changed. A saved adapter is about 20.2 MB in FP32; it needs the pinned base model when loaded. It is not a standalone replacement for all model weights.

## Repeat it

Inside WSL, from the repository root:

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv sync --locked
uv run python -m shellm_training \
  --config configs/training/lora-pilot-v1.json \
  --run-id my-new-lora-run
uv run python tools/evaluate_checkpoints.py --run-id my-new-lora-run
uv run python translate.py "enter the root directory" \
  --adapter checkpoints/my-new-lora-run/epoch-3
```

Training refuses an existing run ID. `translate.py` prints the generated command and does not execute it. Evaluation uses fresh Docker containers and the same raw prompt, greedy decoding, EOS/newline stopping, and 64-token cap as the functional Base baseline. Model outputs, generation metadata, and per-case results are preserved for each epoch. Historical Base reports are preserved, with a separate replay using the current evaluator/image.

## Results

Training completed successfully: **189 optimizer updates**, 3,024 examples seen across three passes, **zero overflow-skipped updates**, and verified changes to adapter weights. Training took **917.3 seconds (15.3 minutes)**, including held-out loss measurements and checkpoint saves but excluding initial model loading. Peak PyTorch tensor allocation was **1.396 GiB**.

| Checkpoint | Optimizer steps | Held-out completion loss |
| --- | ---: | ---: |
| Before training | 0 | 1.251424 |
| Epoch 1 | 63 | 0.007686 |
| Epoch 2 | 126 | 0.007499 |
| Epoch 3 | 189 | 0.007275 |

The run saved adapters after all three epochs. Each was scored on all 112 evaluation requests, requiring both independent filesystem fixtures to pass.

| Model | Functional passes | Functional accuracy | Exact matches | Syntax / format accepted |
| --- | ---: | ---: | ---: | ---: |
| Untouched Base replay | 30 / 112 | 26.8% | 14 / 112 | 108 / 111 |
| LoRA epoch 1 | 78 / 112 | 69.6% | 62 / 112 | 112 / 112 |
| LoRA epoch 2 | 89 / 112 | 79.5% | 59 / 112 | 112 / 112 |
| LoRA epoch 3 | **90 / 112** | **80.4%** | 60 / 112 | 112 / 112 |

The last column lists two counts, each out of 112: syntax then format. All functional passes also passed format. Output format still includes inference-time newline stopping, so the format score should not alone be interpreted as learned EOS behavior.

Epoch 3 is the best overall development checkpoint in this run. It improves functional accuracy by **53.6 percentage points** over Base. Relative to the Base predictions, 61 requests became correct and one became incorrect, for a net gain of 60. The regression is `rm-04`: dropping `docs/` from `docs/old.log` deletes a different existing file, which the filesystem comparison correctly rejects.

The standalone script was also checked with the user's original example: **`enter the root directory` printed `pwd`, rather than `cd /`**, using epoch 3. This is an additional observed translation failure, outside the 112-case suite. That output was printed only; we did not execute it or include it in the functional score. See [the smoke-check record](../reports/2026-10-01-lora-pilot-v1/standalone-smoke-check.json). In contrast, the suite's `change directory to the filesystem root` produced `cd /` and passed both fixtures. Broader root-directory wording belongs in the next data iteration, using new paraphrases rather than copying evaluation prompts.

Exact match did not improve monotonically with functionality. For example, epoch 2/3 outputs use additional valid quotes around ordinary filenames and shell-escaped apostrophes. These can fail exact match and still behave correctly. Epoch 3 has 30 functional passes whose command differs from the reference string.

### Functional results by family

Each cell is passes out of eight development requests.

| Family | Base | Epoch 1 | Epoch 2 | Epoch 3 |
| --- | ---: | ---: | ---: | ---: |
| pwd | 2 | 8 | 8 | 8 |
| cd | 3 | 5 | 6 | 6 |
| ls | 1 | 2 | 6 | 6 |
| mkdir | 2 | 6 | 7 | 7 |
| touch | 1 | 6 | 6 | 6 |
| cp | 2 | 7 | 8 | 8 |
| mv | 3 | 5 | 6 | 6 |
| rm | 3 | 4 | 5 | 5 |
| cat | 1 | 7 | 7 | 8 |
| head | 2 | 7 | 7 | 7 |
| tail | 5 | 7 | 6 | 6 |
| wc | 2 | 7 | 7 | 7 |
| grep | 2 | 2 | 7 | 7 |
| find | 1 | 5 | 3 | 3 |

The overall best epoch regresses in `find` and `tail` relative to epoch 1. Eight requests per family are too few for broad quality claims; retain these results as development evidence.

### Remaining failures and what to learn next

Epoch 3 fails 22 requests. Representative raw generated commands, stripped of their leading formatting space:

| Request | Generated command | Problem |
| --- | --- | --- |
| create a directory called project drafts | `mkdir project drafts` | Creates two directories instead of quoting one name |
| switch to /workspace/src | `mv /workspace/src /workspace/src` | Selects move instead of changing directory |
| delete docs/old.log | `rm old.log` | Drops a path component and deletes the wrong file |
| list every entry here including dotfiles | `ls -d .` | Lists the directory itself rather than its entries |
| give me the bottom 3 lines from numbers.txt | `head -n 3 numbers.txt` | Confuses bottom with top |
| find regular .log files recursively that are larger than 100 bytes | `find . -type f -size +100c` | Omits the extension condition |

These examples were executed only inside the disposable evaluator. A syntactically valid command can still select the wrong operation, arguments, or conditions. Very low validation loss alongside 80.4% functional accuracy demonstrates the limits of our shared-template validation split.

The next proposed milestone is a new dataset release with broader phrasing, independent argument variation, quoting/path extraction coverage, and controlled combinations of search conditions. Add separate composition and paraphrase holdouts before another training comparison. Do not copy these development prompts into training.

### Saved artifacts

- [Training metadata](../reports/2026-10-01-lora-pilot-v1/training-metadata.json) and [per-step log](../reports/2026-10-01-lora-pilot-v1/training-log.jsonl).
- Functional results: [Base replay](../reports/2026-10-01-lora-pilot-v1/evaluations/baseline/evaluation.json), [epoch 1](../reports/2026-10-01-lora-pilot-v1/evaluations/epoch-1/evaluation.json), [epoch 2](../reports/2026-10-01-lora-pilot-v1/evaluations/epoch-2/evaluation.json), [epoch 3](../reports/2026-10-01-lora-pilot-v1/evaluations/epoch-3/evaluation.json).
- [Chart-ready history](../reports/history.csv), including the original Base record and the separate replay. Adjacent files retain raw predictions and generation metadata.
- Best overall adapter: `checkpoints/2026-10-01-lora-pilot-v1/epoch-3/` (ignored by Git).

## Interpretation and limitations

Completion loss measures prediction of command tokens, not shell behavior. A low loss on our small validation split can reflect shared phrasing templates and easy argument substitutions. Functional results use two fixtures, not every possible Linux environment. The suite is a development set; selecting an epoch based on it is model development, not a blinded test claim.

This trainer does not save optimizer state or resume interrupted training. CUDA kernels are not forced to be fully deterministic, so the recorded seed/settings do not promise bit-identical retraining. Training/inference memory values report PyTorch tensor allocations, excluding desktop use and other CUDA overhead. No browser runtime, quantization, merged model, or model-host upload is part of this milestone.

References: [PEFT LoRA documentation](https://huggingface.co/docs/peft/developer_guides/lora), [PEFT precision troubleshooting](https://huggingface.co/docs/peft/developer_guides/troubleshooting), [PyTorch mixed precision examples](https://docs.pytorch.org/docs/stable/notes/amp_examples.html).
