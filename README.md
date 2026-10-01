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
  --predictions reports/base-functional-baseline/predictions.jsonl
```

The [evaluator guide](docs/functional-shell-evaluation.md) explains generation and replay. The [baseline report](docs/functional-baseline-results.md) links to saved predictions, settings, and detailed results. The next milestone is a small validated training dataset.
