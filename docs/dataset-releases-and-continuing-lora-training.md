# Dataset releases and continuing LoRA training

Date: 2026-10-02 (Europe/Budapest).

## Purpose

Explain two independent choices when extending the project: which examples a dataset release contains, and which model/adapter weights initialize the next experiment. This is an explanation and recommendation; no new dataset or training run was created.

## What our current code does

Inspected `configs/training/lora-pilot-v1.json`, `shellm_training/__main__.py`, and the training data contribution guide. The configuration selects exactly one `dataset_release`. The trainer loads that release, trains only its `train` rows, and evaluates loss on its `validation` rows. It loads the pinned Qwen Base weights and creates a fresh LoRA adapter with `get_peft_model`. It does not automatically combine releases or load an earlier trained adapter.

## Dataset versions are complete snapshots

For the next release, the proposed convention is:

```text
pilot-v1 = existing examples and their train/validation assignments
pilot-v2 = retained v1 examples + reviewed additions
next training configuration: dataset_release = pilot-v2
```

The contribution guide already recommends copying the old source catalogs into a new release directory and extending them. Train on the v2 training split alone: it contains the retained old examples and additions. Loading v1 as well would duplicate the retained examples and change their sampling weight. Preserve v1 unchanged so previous experiments remain reproducible.

Keep existing validation examples held out, keep paraphrase groups together, and assign new scenarios to train/validation deliberately. Extra remains outside both splits. A release can technically contain only additions, but that would be a different data convention that must be explicit in the experiment metadata.

## Two ways to initialize the next LoRA experiment

| Approach | Initial weights | Training examples | Main tradeoff |
| --- | --- | --- | --- |
| Fresh LoRA run | Same pretrained Qwen Base + fresh adapter | Full v2 training split | Simple, reproducible comparison; repeats adapter training on old examples |
| Continued adapter training | Same Base + saved trained LoRA | New examples, usually mixed with retained old training examples | Keeps earlier adaptation and can save work; requires explicit loading and careful sampling |

A fresh LoRA run retains Qwen's pretrained English and shell knowledge. Only the small task-specific adapter starts fresh; this does not repeat Qwen pretraining.

It is possible to continue an existing adapter using only additions. Old examples are not a mathematical requirement. However, later updates can degrade earlier behavior (catastrophic forgetting) or overemphasize the newest examples. Mixing old examples back into training (replay) helps maintain coverage; validation should measure whether earlier capabilities actually remain intact. The appropriate mixture depends on the new data and observed validation results.

Loading saved adapter weights for continued training requires a new trainer option. Our current code does not implement this. An adapter warm start with a fresh optimizer/schedule is also different from an exact interrupted-run resume, which would additionally need saved optimizer, scheduler, and other training state.

## Recommendation and next step

For the next small experiment, propose a complete pilot-v2 snapshot and a fresh LoRA run from the same pinned Base, using v2's training split. This is the simplest comparison with the pilot and fits our current trainer. The original pilot took about 15 minutes; the runtime of a larger v2 has not been measured. Continued training with replay can become a separate experiment later if needed.

No training outcome for either v2 approach has been observed. Primary development remains based on validation; Extra is reserved for periodic milestone measurements. Discuss the desired new capabilities and validation coverage before authoring the next release.
