# Translator scope and evaluation plan

Proposed on 2026-10-01 and implemented that day following the user's approval. The original plan is retained below; the completion record links to the final implementation.

## Completion record

Established the [pilot task contract](translator-task-contract.md), authored 112 evaluation cases across 14 command families, implemented and tested the [Docker functional evaluator](functional-shell-evaluation.md), and saved the [untouched Base model's baseline](functional-baseline-results.md). All references passed independent intent checks on two fixtures. The model passed 30 of 112 requests functionally.

The training pilot proposed below remains future work. Ambiguous-request behavior and a separate final test set remain open.

## Why this comes next

We can run both checkpoints, but twelve hand-picked prompts cannot tell us whether training improves generalization. Before fine-tuning, define what counts as a correct answer and write a small evaluation set that training will not consume.

## Proposed first task contract

- Target Ubuntu/Linux with Bash and GNU command-line tools.
- Input is a short, standalone English request. Relative paths refer to the current directory; paths and names should be preserved exactly.
- Output is one command line, with no explanation or Markdown. A single line can eventually contain a pipeline.
- Begin with explicit requests whose arguments and intended action are clear. Decide clarification behavior before adding ambiguous requests to training.
- Start with ordinary navigation, file operations, listing, and text search. Expand multi-stage pipelines after the simple baseline is measurable.

Proposed initial capabilities:

| Capability | Commands |
| --- | --- |
| Navigation and listing | `pwd`, `cd`, `ls` |
| Create files and directories | `touch`, `mkdir` |
| Copy, rename, remove | `cp`, `mv`, `rm` |
| Read and count text | `cat`, `head`, `tail`, `wc` |
| Search | `grep`, `find` |

This is a pilot scope. The broader 20-30-family taxonomy from the initial discussion can grow from it.

## Proposed next deliverables

1. A versioned task specification stating shell assumptions, output format, and treatment of ambiguous inputs.
2. About 100-200 manually reviewed evaluation cases spanning the pilot capabilities, including spaces and punctuation in arguments.
3. A runner that records the exact prompt, raw completion, extracted command, generation settings, package versions, and model revision.
4. A baseline report for our selected checkpoint before training.

Stop and review those deliverables before generating the training pilot.

## Evaluation design

Separate semantic command correctness from output-format compliance. A correct first line followed by an explanation fails the intended format even if the command itself is useful.

Track exact match for a strict baseline, and accept explicitly reviewed equivalent forms where appropriate. General-purpose shell canonicalization is difficult: quoting, option order, redirects, and pipelines can change meaning. Do not normalize these away blindly.

Functional evaluation should later use controlled fixtures and compare outputs or filesystem effects. Reference and generated commands must run against independent copies of the same fixture. Checking `cd` requires observing the working directory within the same shell process; checking syntax alone cannot establish its behavior. ShellCheck can help find shell issues but cannot prove that an English request was translated correctly.

Use dedicated paraphrase, argument, and composition holdouts. Keep paraphrases of the same concrete command together when splitting data. A command-family holdout can be a separate generalization experiment. The existing twelve smoke-test requests are already familiar to the project and should remain diagnostic examples rather than becoming an untouched final test set.

## Training pilot after evaluation

Propose roughly 500-2,000 reviewed training examples for the first workflow experiment. This size is for learning and debugging the training loop, not a claim that it will deliver production accuracy. Scale toward the originally discussed 50,000-100,000 examples only after validation and error analysis show where more data helps.

Construct commands first, validate their semantics and quoting, and then write paraphrases that describe those exact commands. For training, keep the `Request: ...\nCommand:` prefix, calculate loss on the completion tokens, and include EOS after the desired command. The checkpoint, LoRA configuration, and memory requirements will be checked when implementing that training milestone.
