"""Interactive prompt for a saved LoRA adapter: type a request, get a command. Never executes anything."""

import argparse
import sys

from peft import PeftConfig, PeftModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, help="e.g. checkpoints/<run-id>/epoch-3")
    args = parser.parse_args()
    config = PeftConfig.from_pretrained(args.adapter)
    if not config.revision:
        raise SystemExit("Adapter must specify its pinned base model revision")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"Loading {config.base_model_name_or_path} with {args.adapter} on {device}...", file=sys.stderr, flush=True)
    tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path, revision=config.revision)
    base = AutoModelForCausalLM.from_pretrained(config.base_model_name_or_path, revision=config.revision, dtype=dtype).to(device)
    model = PeftModel.from_pretrained(base, args.adapter).eval()
    print("Type a request and press Enter (empty line or Ctrl-D to quit). Commands are printed, never run.\n")
    while True:
        try:
            request = input("Request> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not request:
            break
        inputs = tokenizer(f"Request: {request}\nCommand:", return_tensors="pt").to(device)
        with torch.inference_mode():
            output = model.generate(**inputs, do_sample=False, max_new_tokens=64, stop_strings=["\n"],
                                    tokenizer=tokenizer, pad_token_id=tokenizer.eos_token_id)
        completion = tokenizer.decode(output[0, inputs.input_ids.shape[-1]:], skip_special_tokens=True)
        print(f"Command>{completion.rstrip()}\n")


if __name__ == "__main__":
    main()
