"""Compare Qwen3 checkpoints on a few shell translation prompts."""

import argparse

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_REQUESTS = [
    "enter the root directory",
    "list all files including hidden ones",
    "show my current directory",
    "create a directory called projects",
    "go to my home directory",
    "show the first five lines of README.md",
    "count the lines in report.txt",
    "copy a.txt to b.txt",
    "rename old.txt to new.txt",
    "delete the file old.log",
    "find all .log files under the current directory",
    "search recursively for TODO in the current directory",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requests", nargs="*", default=DEFAULT_REQUESTS)
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B-Base")
    parser.add_argument("--prompt-style", choices=("raw", "chat"), default="raw")
    parser.add_argument("--max-new-tokens", type=int, default=32)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is unavailable in this WSL environment")

    print(f"GPU: {torch.cuda.get_device_name(0)}", flush=True)
    print(f"Loading: {args.model}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=torch.float16,
    ).to("cuda")
    model.eval()

    for request in args.requests:
        if args.prompt_style == "chat":
            messages = [
                {
                    "role": "system",
                    "content": "Translate the user's request into one Linux shell command. Reply with only the command, with no Markdown or explanation.",
                },
                {"role": "user", "content": request},
            ]
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        else:
            prompt = f"Request: {request}\nCommand:"
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=args.max_new_tokens,
                pad_token_id=tokenizer.eos_token_id,
            )
        completion = tokenizer.decode(
            output[0, inputs.input_ids.shape[-1] :], skip_special_tokens=True
        )
        first_line = completion.splitlines()[0].strip() if completion else ""
        print(
            f"Request: {request}\nFirst line: {first_line!r}\nRaw completion: {completion!r}\n",
            flush=True,
        )

    peak_gib = torch.cuda.max_memory_allocated() / 1024**3
    print(f"Peak PyTorch GPU allocation: {peak_gib:.2f} GiB", flush=True)


if __name__ == "__main__":
    main()
