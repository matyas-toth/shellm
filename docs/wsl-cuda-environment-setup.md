# WSL and CUDA environment setup

Experiment date: 2026-09-28. Documented: 2026-10-01.

## What we checked

The project is at `C:\Users\reign\Documents\ChatGPT\SheLLM-0.6B-Project`, accessible in WSL at `/mnt/c/Users/reign/Documents/ChatGPT/SheLLM-0.6B-Project`.

| Item | Observed value |
| --- | --- |
| WSL distribution | Ubuntu, WSL2 |
| Python in WSL | 3.12.3 |
| uv executable | `/home/reign/.local/bin/uv` |
| GPU | NVIDIA GeForce RTX 2060 |
| GPU memory | 6,144 MiB total; about 4,509 MiB free at the initial WSL check |
| Compute capability | 7.5 |
| NVIDIA driver reported by Windows | 610.47 |
| WSL memory | About 15 GiB visible |

Torch, Transformers, Hugging Face Hub, Accelerate, and bitsandbytes were absent from the WSL Python interpreter checked before setup. Free memory is a snapshot and changes as other programs use the GPU.

## What we installed

Created `pyproject.toml`, `.gitignore`, `baseline.py`, and `README.md`. Running `uv sync` produced `uv.lock` and installed the environment on the WSL filesystem at `/home/reign/.venvs/shellm-0.6b`.

The direct dependencies are Torch and Transformers. Important resolved versions recorded in the lockfile are:

| Package | Version |
| --- | --- |
| torch | 2.11.0+cu130 |
| transformers | 4.57.6 |
| huggingface-hub | 0.36.2 |
| safetensors | 0.8.0 |
| tokenizers | 0.22.2 |

`pyproject.toml` assigns Torch to the official CUDA 13.0 wheel index. CUDA runtime libraries were installed as dependencies. We did not separately install a system CUDA compiler for these inference runs. The NVIDIA driver already supported running the selected build.

Training packages from the original discussion, such as PEFT, TRL, datasets, Accelerate, bitsandbytes, and TensorBoard, are still future additions.

## Repeat the setup and run

From an Ubuntu WSL terminal:

```bash
cd /mnt/c/Users/reign/Documents/ChatGPT/SheLLM-0.6B-Project
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/shellm-0.6b"
uv sync --locked
uv run python baseline.py
uv run python baseline.py "enter the root directory"
```

Set `UV_PROJECT_ENVIRONMENT` in each new terminal session. Model files were downloaded through Hugging Face and cached in WSL; they are not committed to the repository. The baseline intentionally uses float16 rather than requesting bfloat16 on this GPU.

## What this establishes

CUDA model loading and inference succeeded in WSL. This confirms that the machine can run the selected model; it does not establish how much memory a training configuration will require.

References: [uv's PyTorch integration guide](https://docs.astral.sh/uv/guides/integration/pytorch/), [PyTorch releases](https://github.com/pytorch/pytorch/releases).
