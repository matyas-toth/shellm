# Pilot evaluation suite

`cases.jsonl` contains 112 task cases, eight per command family. Each record has a stable ID, request, reference, output comparison mode, and coverage label. References are independently validated on two fixtures before predictions are scored.

See the [task contract](../docs/translator-task-contract.md), [functional evaluator guide](../docs/functional-shell-evaluation.md), and [recorded baseline](../docs/functional-baseline-results.md).

The suite is reserved for development evaluation. Do not copy its requests into training data. Changes to cases or checks require documenting the change and recording a new result; scores from different suite versions should not be treated as the same experiment.
