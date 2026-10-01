"""Completion-only labels, EOS supervision, and padding that never contributes loss."""

import torch


def tokenize_record(tokenizer, row, max_length=128):
    prefix = f"Request: {row['request']}\nCommand:"
    prompt_ids = tokenizer.encode(prefix, add_special_tokens=False)
    text_ids = tokenizer.encode(prefix + " " + row["command"], add_special_tokens=False)
    if text_ids[:len(prompt_ids)] != prompt_ids:
        raise ValueError(f"Tokenizer crosses prompt/completion boundary: {row['id']}")
    ids = text_ids + [tokenizer.eos_token_id]
    if len(ids) > max_length:
        raise ValueError(f"Example exceeds max_length; no silent truncation: {row['id']}")
    return {"id": row["id"], "input_ids": ids, "labels": [-100] * len(prompt_ids) + ids[len(prompt_ids):]}


def collate(rows, pad_id, device="cuda"):
    width = max(len(row["input_ids"]) for row in rows)
    ids, labels, masks = [], [], []
    for row in rows:
        missing = width - len(row["input_ids"])
        ids.append(row["input_ids"] + [pad_id] * missing)
        labels.append(row["labels"] + [-100] * missing)
        masks.append([1] * len(row["input_ids"]) + [0] * missing)
    return {"input_ids": torch.tensor(ids, device=device), "labels": torch.tensor(labels, device=device),
            "attention_mask": torch.tensor(masks, device=device)}
