"""Verify unequal-length greedy batches match serial decoding on real Qwen tokens."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from shellbench.__main__ import completed_ids
from shellbench.sandbox import load_cases
from shellbench.suites import suite_path

MODEL = "Qwen/Qwen3-0.6B-Base"
REVISION = "da87bfb608c14b7cf20ba1ce41287e8de496c0cd"
tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
tokenizer.pad_token, tokenizer.padding_side = tokenizer.eos_token, "left"
model = AutoModelForCausalLM.from_pretrained(MODEL, revision=REVISION, dtype=torch.float16).to("cuda").eval()
cases = load_cases(suite_path("shellbench-extra-v1"))
prompts = [f"Request: {cases[index]['request']}\nCommand:" for index in (0, 3, 100, 185)]


def decode(prompts):
    inputs = tokenizer(prompts, padding=True, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        result = model.generate(**inputs, do_sample=False, max_new_tokens=64, stop_strings=["\n"],
                                tokenizer=tokenizer, pad_token_id=tokenizer.eos_token_id)
    return [tokenizer.decode(completed_ids(row[inputs.input_ids.shape[-1]:], tokenizer), skip_special_tokens=True) for row in result]


serial = [decode([prompt])[0] for prompt in prompts]
batched = decode(prompts)
if serial != batched:
    raise RuntimeError(f"Batch/serial differences: {list(zip(serial, batched))}")
print("Four unequal-length prompts matched serial greedy completions exactly; EOS/newline padding trimmed.")
