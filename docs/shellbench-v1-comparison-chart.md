# ShellBench v1 comparison chart

Date: 2026-10-01 (Europe/Budapest).

Created a simple column chart comparing untouched Qwen3 0.6B Base with all three epochs of the first SheLLM LoRA pilot. The displayed name `shellm-lora-pilot-1-epoch-3-0.6b` refers to the local epoch-3 adapter from run `2026-10-01-lora-pilot-v1`; it is not a published model repository ID.

The metric is **functional accuracy**, requiring success on both filesystem fixtures for each of 112 requests. Scores are 26.8%, 69.6%, 79.5%, and 80.4%. The percentage axis starts at zero and ends at 100. The chart uses the Base replay and epoch reports scored with identical suite, evaluator, and image fingerprints. It shows the development benchmark, with its existing generalization limits.

Artifacts: [PNG](../reports/2026-10-01-lora-pilot-v1/charts/shellbench-v1-functional-accuracy.png), [editable SVG](../reports/2026-10-01-lora-pilot-v1/charts/shellbench-v1-functional-accuracy.svg), and [source CSV](../reports/2026-10-01-lora-pilot-v1/charts/shellbench-v1-functional-accuracy.csv).

`tools/plot_shellbench.py` reads the saved evaluation reports directly. It needs Matplotlib; the chart was generated using version 3.10.7 in Codex's bundled Python runtime, without changing training dependencies. To regenerate using a Python environment with Matplotlib:

```bash
python tools/plot_shellbench.py --run-id 2026-10-01-lora-pilot-v1
```

The PNG was visually checked for readable labels and correct values. No model inference or evaluations were rerun. Future charts can read the preserved experiment reports and history CSV.
