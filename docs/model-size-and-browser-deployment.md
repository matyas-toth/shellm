# Model size and browser deployment

Discussion date: 2026-09-28. Documented: 2026-10-01.

The user asked whether we could go below 0.6B parameters without losing too much language understanding. We identified [SmolLM2-360M](https://huggingface.co/HuggingFaceTB/SmolLM2-360M) as an English-focused candidate. Qwen2.5 also has a 0.5B checkpoint. Neither was downloaded, evaluated, or trained in this project.

There is no demonstrated 0.6B cutoff for this task. Pretraining quality, architecture, and task data matter alongside parameter count. Our working expectation is that smaller models may struggle more with unfamiliar wording and composed requests; only a shared shell evaluation set can measure that tradeoff here.

The provisional choice is to learn the training workflow using the already working Qwen3 0.6B model, then compare a smaller checkpoint using the same task data and evaluation cases.

## Quantization and the browser goal

Quantization stores weights using fewer bits. Reducing parameter count changes the model itself. Both can reduce deployment size, but their effects on task accuracy must be measured.

For a nominal 600 million parameters, arithmetic weight storage alone is about 1.2 GB at 16 bits or 0.3 GB at 4 bits. These are rough calculations, not measurements of a deployable artifact: scales, metadata, buffers, caches, and implementation choices add overhead.

Future browser inference will also require tokenization, model operations, generation, and stopping behavior. A chat template is text formatting performed before tokenization; using it does not require an extra transformer kernel. Our planned plain prefix is an interface choice that training can teach either checkpoint to follow, although neither has been trained on it yet.

No quantization, WebGPU kernels, browser UI, performance benchmarks, or model uploads have been implemented. These remain later milestones after we establish task accuracy.
