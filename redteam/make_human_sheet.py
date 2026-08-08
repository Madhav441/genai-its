#!/usr/bin/env python3
"""Generate a blind coding sheet for the human second coder.

Emits human_coding_sheet.csv: the same 38 verification trials, randomised, with the
automated label, breach flag and condition withheld so the coder judges independently.
A hidden key (human_sheet_key.csv) preserves the mapping for scoring; do not send it
to the coder.
"""
import csv, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "results", "raw_results.csv")
ITEMS = os.path.join(HERE, "items.csv")

# the 38 verification trials: all flagged + the stratified sample (seed 2026)
def verification_indices(rows):
    import collections
    flagged = [i for i, r in enumerate(rows) if r["needs_human_review"] == "1"]
    rest = [i for i, r in enumerate(rows) if r["needs_human_review"] != "1"]
    by = collections.defaultdict(list)
    for i in rest:
        by[(rows[i]["condition"], rows[i]["label"])].append(i)
    rng = random.Random(2026)
    sample = []
    for k in sorted(by):
        v = by[k][:]; rng.shuffle(v); sample += v[:8]
    return flagged + sample

def main():
    rows = list(csv.DictReader(open(RAW, encoding="utf-8")))
    items = {r["item_id"]: r for r in csv.DictReader(open(ITEMS, encoding="utf-8"))}
    idxs = verification_indices(rows)
    rng = random.Random(7)
    rng.shuffle(idxs)

    sheet = os.path.join(HERE, "human_coding_sheet.csv")
    key = os.path.join(HERE, "human_sheet_key.csv")
    with open(sheet, "w", newline="", encoding="utf-8") as f, \
         open(key, "w", newline="", encoding="utf-8") as kf:
        w = csv.writer(f); k = csv.writer(kf)
        w.writerow(["code_id", "question", "reference_answer", "model_output", "breach", "note"])
        k.writerow(["code_id", "row_idx", "condition", "family", "auto_label", "auto_breach"])
        for n, i in enumerate(idxs, 1):
            r = rows[i]
            it = items.get(r["item_id"], {})
            w.writerow([f"C{n:02d}", it.get("question", "")[:400],
                        it.get("correct_answer", "")[:400], r["output"], "", ""])
            k.writerow([f"C{n:02d}", i, r["condition"], r["family"], r["label"], r["breach"]])
    print(f"Wrote {sheet} ({len(idxs)} rows) - send this to the coder.")
    print(f"Wrote {key} - keep private, needed for scoring.")

if __name__ == "__main__":
    main()
