# SheLLM

An experimental small model for translating English requests into Linux shell commands.

## Project documentation

The [project notebook](docs/README.md) records setup, experiment results, decisions, and proposed next steps. Each milestone or topic has a descriptive Markdown document in `docs/`.

## Milestone 1: run the untouched base model

Use WSL Ubuntu from this repository directory. Keep the Python environment on the WSL filesystem; the model download is cached there too.

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv sync --locked
uv run python baseline.py
uv run python baseline.py "enter the root directory"
```

The baseline script loads `Qwen/Qwen3-0.6B-Base` in float16 on CUDA and uses the proposed `Request: ...\nCommand:` format. Its output is a pretraining baseline, not a trained shell translator. The script only prints generated text; it never executes it.

## Milestone 2: compare the instruction-tuned checkpoint

```bash
uv run python baseline.py --model Qwen/Qwen3-0.6B
uv run python baseline.py --model Qwen/Qwen3-0.6B --prompt-style chat
```

The first command keeps the raw prompt identical to the base-model run. The second uses Qwen's chat template in non-thinking mode with an instruction to return one command. The script's twelve fixed requests are an exploratory smoke test, not a benchmark score.

See the [full comparison and limitations](docs/qwen-base-versus-instruction-tuned-comparison.md).

## Milestone 3: functional evaluation

The [pilot suite](eval/README.md) covers 112 requests across 14 command families. Commands run in disposable Docker containers and are checked on two filesystem fixtures. The untouched Base model passed 30/112 requests functionally; only 14/112 matched the reference command string.

With Docker Desktop running, use the same WSL environment:

```bash
uv run python -m shellbench build
uv run python -m shellbench validate
uv run python -m unittest discover -s tests -v
uv run python -m shellbench evaluate \
  --predictions reports/base-functional-baseline/predictions.jsonl \
  --output reports/baseline-replay.json
```

The [evaluator guide](docs/functional-shell-evaluation.md) explains generation and replay. The [baseline report](docs/functional-baseline-results.md) links to saved predictions, settings, and detailed results.

## Milestone 4: validated data and LoRA

The [training dataset](data/shell_translation/README.md) keeps 1,008 training and 112 validation examples in topic/family folders, with editable intent catalogs and fully rendered JSONL releases. See the [contribution guide](docs/training-data-contribution-guide.md) to extend it.

The [first LoRA experiment](docs/first-lora-training-experiment.md) completed three epochs on the RTX 2060 in about 15 minutes, with 1.40 GiB peak PyTorch tensor allocation. Functional accuracy improved from 30/112 (26.8%) to 90/112 (80.4%). This is a development-suite result; quoting, path interpretation, and search composition still need work. The separate smoke request `enter the root directory` currently prints `pwd`, showing that broader wording also needs attention.

```bash
uv run python -m shellm_data build --release pilot-v1 --check
uv run python -m shellm_data validate --release pilot-v1
uv run python -m shellm_training \
  --config configs/training/lora-pilot-v1.json \
  --run-id my-lora-experiment
uv run python -m shellbench generate \
  --adapter checkpoints/my-lora-experiment/epoch-3 \
  --output reports/my-lora-experiment/evaluations/epoch-3
uv run python -m shellbench evaluate \
  --predictions reports/my-lora-experiment/evaluations/epoch-3/predictions.jsonl
uv run python tools/report_history.py
```

Try the saved best overall checkpoint inside WSL:

```bash
uv run python translate.py "enter the root directory" \
  --adapter checkpoints/2026-10-01-lora-pilot-v1/epoch-3
```

`translate.py` prints the command. Use `uv run python tools/evaluate_checkpoints.py --run-id my-lora-experiment` to generate and evaluate every saved epoch of another completed run.

Use a fresh run ID for each experiment. Checkpoints are ignored by Git; dataset releases, configurations, training logs, and evaluation reports are intended to be tracked. New prediction directories and evaluation files refuse overwrites to preserve history. `reports/history.csv` is a regenerable chart index; original reports remain authoritative.
