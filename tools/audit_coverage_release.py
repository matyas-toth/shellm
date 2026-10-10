"""Check pilot-v2 separation/tokenization and export a compact human review pack.

No model weights are loaded and no optimizer or training code is invoked.
"""

from collections import Counter, defaultdict
import hashlib
import json
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from transformers import AutoTokenizer
from shellbench.extra_audit import audit
from shellbench.sandbox import ROOT, load_cases
from shellbench.suites import suite_path
from shellm_data.core import DATA, build, check_records, load_release, source_groups
from shellm_data.intents import render
from shellm_training.data import tokenize_record
from tools.build_coverage_catalog import PREFIX, TRAIN_NAMES, VALIDATION_NAMES, author
from tools.lint_requests import skeleton


def main():
    rows, manifest = load_release("pilot-v2")
    assert build("pilot-v2", check=True) == manifest
    old = source_groups("pilot-v1")
    groups = source_groups("pilot-v2")
    without_source = lambda g: {k: v for k, v in g.items() if k != "source"}
    actual = {g["id"]: without_source(g) for g in groups}
    assert {g["id"]: actual[g["id"]] for g in old} == {g["id"]: without_source(g) for g in old}
    assert {g["id"]: g for g in author()} == actual, "Catalogs differ from the checked authoring matrix"
    added_groups = [g for g in groups if g["id"].startswith(PREFIX)]
    added = [r for r in rows if r["group_id"].startswith(PREFIX)]

    def strings(value):
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [s for v in value for s in strings(v)]
        if isinstance(value, dict):
            return [s for k, v in value.items() if k != "op" for s in strings(v)]
        return []

    labels = defaultdict(set)
    sentence_banks = defaultdict(lambda: defaultdict(set))
    for g in groups:
        labels[render(g["intent"])].add(g["split"])
        if not g["id"].startswith(PREFIX):
            continue
        forbidden = VALIDATION_NAMES if g["split"] == "train" else TRAIN_NAMES
        assert not any(root in s for root in forbidden for s in strings(g["intent"])), g["id"]
        for request in g["requests"]:
            sentence_banks[g["family"]][g["split"]].add(skeleton(request, g["intent"]))
    new_labels = {r["command"] for r in added}
    overlaps = {label for label in new_labels if len(labels[label]) != 1}
    assert not overlaps, overlaps
    for family, banks in sentence_banks.items():
        assert not banks["train"] & banks["validation"], family
    extra_report = audit(load_cases(suite_path("shellbench-extra-v1")))
    lint = subprocess.run([sys.executable, "tools/lint_requests.py", "--release", "pilot-v2", "--all", "--group-prefix", PREFIX],
                          cwd=ROOT, capture_output=True, text=True, check=True)

    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base", revision="da87bfb608c14b7cf20ba1ce41287e8de496c0cd", local_files_only=True)
    lengths, prompt_lengths, completion_lengths = [], [], []
    longest = None
    for number, row in enumerate(rows, 1):
        tokens = tokenize_record(tokenizer, row, max_length=128)
        start = next(i for i, label in enumerate(tokens["labels"]) if label != -100)
        assert tokenizer.decode(tokens["input_ids"][:start]) == f"Request: {row['request']}\nCommand:"
        assert tokenizer.decode(tokens["labels"][start:-1]) == " " + row["command"]
        assert tokens["labels"][-1] == tokenizer.eos_token_id
        length = len(tokens["input_ids"])
        if longest is None or length > longest["tokens"]:
            longest = {"id": row["id"], "tokens": length}
        lengths.append(length)
        prompt_lengths.append(start)
        completion_lengths.append(length - start)
        if number % 5000 == 0:
            print(f"Checked token boundaries, masks and EOS for {number}/{len(rows)} examples", flush=True)

    metadata = DATA / "authoring/pilot-v2"
    coverage = json.loads((metadata / "coverage.json").read_text())
    coverage["summary"] = check_records(rows)
    (metadata / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    report = {"date": "2026-10-10", "release": "pilot-v2", "dataset_sha256": manifest["dataset_sha256"],
              "parent_preserved_groups": len(old), "authoring_matrix_matches_catalogs": True,
              "added_examples": len(added), "added_splits": dict(Counter(r["split"] for r in added)),
              "new_label_train_validation_overlap": len(overlaps), "new_sentence_bank_overlap": 0,
              "argument_pool_overlap": len(set(TRAIN_NAMES) & set(VALIDATION_NAMES)),
              "new_training_sentence_shapes_by_family": {f: len(b["train"]) for f, b in sentence_banks.items()},
              "new_validation_sentence_shapes_by_family": {f: len(b["validation"]) for f, b in sentence_banks.items()},
              "lint": lint.stdout.strip(), "extra_audit": extra_report,
              "tokenization": {"examples": len(rows), "tokenizer": "Qwen/Qwen3-0.6B-Base",
                               "revision": "da87bfb608c14b7cf20ba1ce41287e8de496c0cd", "max_length_limit": 128,
                               "longest": longest, "total_tokens": sum(lengths),
                               "prompt_tokens": sum(prompt_lengths), "supervised_completion_tokens": sum(completion_lengths),
                               "mean_tokens": round(sum(lengths) / len(lengths), 2), "silent_truncations": 0,
                               "all_boundaries_masks_and_eos_checked": True},
              "authoring_script_sha256": hashlib.sha256((ROOT / "tools/build_coverage_catalog.py").read_bytes()).hexdigest(),
              "benchmark_hashes": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (ROOT / "eval/cases.jsonl", suite_path("shellbench-extra-v1"))},
              "training_started": False,
              "limits": ["Template-based authored English; requests still need human semantic review.",
                         "New internal validation holds out wording and argument roots together; it is not a dedicated composition holdout.",
                         "Inherited validation remains unchanged and has the parent's weaker separation.",
                         "ShellBench v1 is now a development diagnostic, not an untouched test.",
                         "Existing utility oracle limitations still apply to inherited examples."]}
    (metadata / "quality.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Pilot v2 review pack", "", "2026-10-10 (Europe/Budapest). Data prepared; no training started.", "",
             "These samples are for human review of meaning. Every command is also covered by the release's Docker validation; that does not prove the English paraphrases are correct.", "",
             "## Added coverage", "", "| Capability | Groups | Examples |", "| --- | ---: | ---: |"]
    for capability, count in sorted(Counter(g["capability"] for g in added_groups).items()):
        lines.append(f"| {capability} | {count} | {count * 6} |")
    by_capability = defaultdict(list)
    for g in added_groups:
        by_capability[g["capability"]].append(g)
    for capability, candidates in sorted(by_capability.items()):
        lines += ["", "## " + capability, ""]
        for split in ("train", "validation"):
            choices = [g for g in candidates if g["split"] == split]
            if not choices:
                continue
            # Two different literal argument shapes for each capability/split.
            for g in (choices[0], choices[len(choices) // 2]):
                lines += [f"### {g['id']} ({split})", "", "```json", json.dumps(g["intent"], ensure_ascii=False), "```", "", "```bash",
                          render(g["intent"]), "```", ""]
                lines += ["- " + request for request in g["requests"]]
    (metadata / "review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("extra_audit", "new_training_sentence_shapes_by_family", "new_validation_sentence_shapes_by_family")}, indent=2))


if __name__ == "__main__":
    main()
