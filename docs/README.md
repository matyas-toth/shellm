# SheLLM project notebook

Created on 2026-10-01. This notebook backfills the work performed on 2026-09-28 and records future milestones as they happen.

| Document | What it covers | Status |
| --- | --- | --- |
| [Project goals and roadmap](project-goals-and-roadmap.md) | Learning goals, intended product, completed milestones, future work | Living overview |
| [WSL and CUDA environment setup](wsl-cuda-environment-setup.md) | Hardware checks, installed packages, environment location, repeatable setup | Completed |
| [Qwen Base inference baseline](qwen-base-inference-baseline.md) | First GPU inference run, prompt format, outputs, memory measurement | Completed |
| [Base versus instruction-tuned comparison](qwen-base-versus-instruction-tuned-comparison.md) | Twelve requests, exact first-line outputs, interpretation and limitations | Completed |
| [Model size and browser deployment](model-size-and-browser-deployment.md) | Discussion of smaller models, quantization, and later browser work | Discussed; smaller models untested |
| [Translator scope and evaluation plan](translator-scope-and-evaluation-plan.md) | Original proposal and completion record | Evaluation milestone completed |
| [Translator task contract](translator-task-contract.md) | Pilot interface, Linux assumptions, 14 families, scope and success criteria | Established |
| [Functional shell evaluation](functional-shell-evaluation.md) | Docker fixtures, independent reference validation, checks, tests, repeatable commands | Implemented and verified |
| [Functional baseline results](functional-baseline-results.md) | 112-case Base baseline, per-family scores and saved artifacts | Completed |
| [Validated training dataset](validated-training-dataset.md) | 1,008 training examples, held-out validation, 560 label checks, and data layout | Completed |
| [Training data contribution guide](training-data-contribution-guide.md) | Extend catalogs, create releases, and add independent intent checks | Contributor guide |
| [Experiment report history](experiment-report-history.md) | Preserved runs, per-epoch reports, and chart-ready history export | Implemented |
| [First LoRA training experiment](first-lora-training-experiment.md) | Three saved adapters, 26.8% to 80.4% functional accuracy, and failure analysis | Completed |
| [ShellBench v1 comparison chart](shellbench-v1-comparison-chart.md) | Column chart comparing Base and three LoRA epochs, with PNG/SVG/CSV exports | Completed |

Each topic should explain what we did, why, how to repeat it, what we observed, and what remains uncertain. Experiment dates and documentation dates are recorded separately when backfilling. Plans are not recorded as completed experiments.
