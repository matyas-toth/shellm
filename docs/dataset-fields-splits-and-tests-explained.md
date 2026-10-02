# Dataset fields, splits, and tests explained

Date: 2026-10-01 (Europe/Budapest).

Purpose: explain the pilot data design to collaborators joining training work. This explanation was checked against the current compiler, tokenizer, trainer, and test files. No dataset, model, split, or score was changed.

## What reaches the model

The model receives text like:

```text
Request: create a directory named backups
Command: mkdir backups<EOS>
```

The input is the request prefix; supervised labels cover the command and EOS. Prompt and padding tokens are excluded from the loss. The trainer selects records by `split`, combines all families into one training collection, and shuffles examples each epoch. Metadata is not included in the model prompt.

## What the fields mean

| Field | Purpose |
| --- | --- |
| `requests` / `request` | A catalog contains several English paraphrases; each rendered training row contains one request. |
| `command` | The desired shell output, generated from the declared intent. Present in rendered rows. |
| `family` | Command category, such as `mkdir`, `grep`, or `find`. Used to organize coverage and report results per category. |
| `topic` | Broader organizational category, such as filesystem or navigation. |
| `capability` | Human-readable tag for the task being covered, such as directory creation. |
| `intent` | Structured operation and arguments, used to generate a label, create fixtures, and check intended effects. |
| `id` | Stable identifier: a scenario ID in catalogs, an example ID in rendered rows. |
| `group_id` | In rendered rows, links paraphrases back to their common scenario. The entire group stays in one split. |
| `split` | Selects whether the trainer uses the example to update weights or to measure held-out loss. |
| `provenance` | Source catalog, data release, and authoring method for tracing a rendered example. |
| `schema_version` | Version of the rendered record format. |

Family/topic/capability are bookkeeping. In particular, `family` does not create separate models or cause a whole family to be excluded from training. All 14 pilot families appear in both training and validation. It helps ensure reasonable coverage and expose regressions hidden by a single overall score.

## Why intent exists

Example:

```json
{"op": "mkdir", "targets": ["my stuff"]}
```

The renderer creates `mkdir 'my stuff'`. A fixture initially lacks that directory. Independent Python expectations describe the desired resulting state: one new directory named `my stuff`, with existing files preserved. Docker execution checks whether the label actually has that effect. `mkdir my stuff` would instead create two directories and fail the state check.

Intent is data-authoring and verification machinery; the model generates a command directly from English. It does not predict or consume the intent object. An accurate intent/command pair still does not prove the English paraphrase describes that intent correctly; semantic review remains necessary.

## Why not randomly split individual rows?

Random splitting can be appropriate when examples are sufficiently independent and the intended evaluation distribution matches the data. Our four paraphrases per scenario are related. If some appear in training and others in validation, the validation set can become mostly a test of nearly repeated examples.

We therefore split **scenario groups**, keeping all paraphrases together. Randomization is compatible with this: a future release can use a seeded random group split within each family, combined with separate deliberate argument/composition holdouts.

The current pilot uses a simple deterministic split: 18 training scenarios and two validation scenarios per family. Most families reserve the last two argument names (`tundra` and `zephyr`); `pwd` reserves phrasing groups. Counts are 1,008 training and 112 validation examples. This is a deliberate small argument/wording holdout, not a random sample of real-world requests.

The present split is weak in some ways: many templates and option patterns recur across training and validation, and its loss became very low despite meaningful functional failures. A stronger next iteration should evaluate novel wording, arguments, and compositions separately. Avoiding exact evaluation-request overlap does not establish full semantic independence.

## What are the tests?

There are several distinct checks:

1. **Training-label validation:** all 280 catalog scenarios were executed on two generated filesystem fixtures, for 560 command checks. An independent intent oracle checks outputs, working directory, and filesystem effects. Paraphrases sharing a command share this label check.
2. **Software tests:** 20 test methods check the compiler, leakage guards, shell quoting, token masking/EOS/padding, and evaluator behavior. For example, equivalent commands should pass and commands that delete unrelated files should fail. This checks our tooling, not the model's accuracy.
3. **Training validation split:** 112 examples excluded from gradient updates measure command-token cross-entropy before training and after each epoch. This measures prediction of known reference commands under their request prefixes; it does not execute generated commands.
4. **ShellBench v1 development evaluation:** a separate 112-request set, excluded from the training/validation release, asks the model to generate commands and executes them in disposable Docker fixtures. Functional success requires the correct observable behavior on both variants. Epoch 3 passed 90/112, or 80.4%.

Two different 112-example sets happen to have the same size. The training validation set and ShellBench are distinct. ShellBench is used for development feedback and checkpoint comparisons; a separate untouched final test set is still needed for stronger generalization claims.

For example, `ls -la` and `ls -al` can both be functionally correct. Exact string match is retained as a diagnostic, while the benchmark's primary score checks behavior. Every fixture comparison is limited to the effects our current oracle can observe.

## Code and further reading

- [Dataset compiler](../shellm_data/core.py) and [intent renderer/oracle](../shellm_data/intents.py).
- [Training tokenization](../shellm_training/data.py) and [trainer](../shellm_training/__main__.py).
- [Evaluator tests](../tests/test_shellbench.py) and [data/tokenization tests](../tests/test_training_data.py).
- [Contribution guide](training-data-contribution-guide.md), [functional evaluation guide](functional-shell-evaluation.md), and [first experiment results](first-lora-training-experiment.md).

Next proposed work: strengthen the dataset's wording/argument diversity and evaluation splits using the recorded failure patterns. This explanation itself introduces no implementation changes.
