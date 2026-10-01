"""Print a translation using a saved LoRA adapter; does not execute commands."""

import argparse
import sys

from peft import PeftConfig, PeftModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("--adapter", required=True)
    args = parser.parse_args()
    if not args.request.strip() or any(c in args.request for c in "\n\r\0"):
        raise SystemExit("Provide one nonempty single-line request")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this reference inference script")
    config = PeftConfig.from_pretrained(args.adapter)
    if not config.revision:
        raise SystemExit("Adapter must specify its pinned base model revision")
    print(f"Loading {config.base_model_name_or_path} with {args.adapter}", file=sys.stderr, flush=True)
    tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path, revision=config.revision)
    base = AutoModelForCausalLM.from_pretrained(config.base_model_name_or_path, revision=config.revision, dtype=torch.float16).to("cuda")
    model = PeftModel.from_pretrained(base, args.adapter).eval()
    inputs = tokenizer(f"Request: {args.request}\nCommand:", return_tensors="pt").to("cuda")
    with torch.inference_mode():
        output = model.generate(**inputs, do_sample=False, max_new_tokens=64, stop_strings=["\n"],
                                tokenizer=tokenizer, pad_token_id=tokenizer.eos_token_id)
    completion = tokenizer.decode(output[0, inputs.input_ids.shape[-1]:], skip_special_tokens=True)
    print(completion.strip())


if __name__ == "__main__":
    main()
