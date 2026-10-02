# Pilot evaluation suite

`cases.jsonl` contains 112 task cases, eight per command family. Each record has a stable ID, request, reference, output comparison mode, and coverage label. References are independently validated on two fixtures before predictions are scored.

See the [task contract](../docs/translator-task-contract.md), [functional evaluator guide](../docs/functional-shell-evaluation.md), and [recorded baseline](../docs/functional-baseline-results.md).

The suite is reserved for development evaluation. Do not copy its requests into training data. Changes to cases or checks require documenting the change and recording a new result; scores from different suite versions should not be treated as the same experiment.

[ShellBench Extra v1](shellbench-extra-v1/README.md) is a separate 300-case benchmark for periodic long-term progress snapshots. It has independent cases, fixtures, and expectations and is outside the training/validation splits. Select it explicitly with `--suite shellbench-extra-v1`; default commands continue using this original pilot suite.
