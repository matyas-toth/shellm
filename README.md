# SheLLM

An experimental small model for translating English requests into Linux shell commands.

## Milestone 1: run the untouched base model

Use WSL Ubuntu from this repository directory. Keep the Python environment on the WSL filesystem; the model download is cached there too.

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv sync
uv run python baseline.py
uv run python baseline.py "enter the root directory"
```

The baseline script loads `Qwen/Qwen3-0.6B-Base` in float16 on CUDA and uses the proposed `Request: ...\nCommand:` format. Its output is a pretraining baseline, not a trained shell translator. The script only prints generated text; it never executes it.
