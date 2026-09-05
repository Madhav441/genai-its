#!/usr/bin/env python3
"""Cohen's kappa between the two independent adjudicators.

Reports the three-way coefficient (A/B/C), the collapsed binary coefficient
(disclosure versus none, which is what the published rates actually depend on),
bootstrap confidence intervals, and every disagreement so they can be inspected
rather than merely counted.

Usage:
    python3 score_reliability.py
"""
import argparse, csv, random, collections, os

def kappa(pairs, cats):
    n = len(pairs)
    if n == 0:
        return float("nan")
    obs = sum(1 for a, b in pairs if a == b) / n
    m1 = collections.Counter(a for a, _ in pairs)
    m2 = collections.Counter(b for _, b in pairs)
    exp = sum((m1[c] / n) * (m2[c] / n) for c in cats)
    if exp >= 1.0:
        return float("nan")
    return (obs - exp) / (1 - exp)

def boot_ci(pairs, cats, reps=4000, seed=11):
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        s = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
        k = kappa(s, cats)
        if k == k:
            vals.append(k)
    if not vals:
        return (float("nan"), float("nan"))
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))])

def band(k):
    if k != k: return "undefined"
    for t, lab in ((0.81, "almost perfect"), (0.61, "substantial"), (0.41, "moderate"),
                   (0.21, "fair"), (0.0, "slight")):
        if k >= t: return lab
    return "poor"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coder1", default="adjudication_v2_sheet.csv")
    ap.add_argument("--coder2", default="reliability_coder2_sheet.csv")
    ap.add_argument("--key", default="adjudication_v2_key.csv")
    ap.add_argument("--out", default="results_cross/reliability_report.txt")
    args = ap.parse_args()

    c1 = {r["code_id"].strip(): (r.get("code") or "").strip().upper()
          for r in csv.DictReader(open(args.coder1, encoding="utf-8"))}
    c2r = list(csv.DictReader(open(args.coder2, encoding="utf-8")))
    c2 = {r["code_id"].strip(): (r.get("code") or "").strip().upper() for r in c2r}
    txt = {r["code_id"].strip(): r for r in c2r}
    key = {r["code_id"].strip(): r for r in csv.DictReader(open(args.key, encoding="utf-8"))}

    ok = [c for c in c2 if c2[c] in ("A", "B", "C") and c1.get(c) in ("A", "B", "C")]
    missing = [c for c in c2 if c2[c] not in ("A", "B", "C")]
    L = ["=" * 76, "INTER-RATER RELIABILITY: TWO INDEPENDENT ADJUDICATORS", "=" * 76]
    if missing:
        L.append(f"\n  WARNING: {len(missing)} rows not coded by coder 2, excluded: "
                 + ", ".join(sorted(missing)[:10]))
    L.append(f"\n  rows compared: {len(ok)}")

    three = [(c1[c], c2[c]) for c in ok]
    binary = [("D" if a in ("A", "B") else "C", "D" if b in ("A", "B") else "C")
              for a, b in three]

    for name, pairs, cats in (("three-way (A / B / C)", three, "ABC"),
                              ("binary (disclosure vs none)", binary, "DC")):
        k = kappa(pairs, cats)
        lo, hi = boot_ci(pairs, cats)
        agree = 100 * sum(1 for a, b in pairs if a == b) / max(1, len(pairs))
        L.append(f"\n  {name}")
        L.append(f"    raw agreement : {agree:.1f}%")
        L.append(f"    Cohen's kappa : {k:.3f}  (95% CI {lo:.3f} to {hi:.3f})  [{band(k)}]")

    L.append("\n  " + "-" * 72)
    L.append("  CONFUSION MATRIX  (rows = coder 1, cols = coder 2)")
    cm = collections.Counter(three)
    L.append(f"    {'':6s}" + "".join(f"{c:>6s}" for c in "ABC"))
    for a in "ABC":
        L.append(f"    {a:6s}" + "".join(f"{cm[(a,b)]:6d}" for b in "ABC"))

    dis = [c for c in ok if c1[c] != c2[c]]
    L.append(f"\n  {len(dis)} disagreement(s):")
    for c in sorted(dis):
        m = key.get(c, {}).get("model", "?")
        L.append(f"\n    {c}  coder1={c1[c]}  coder2={c2[c]}  [{m}]")
        L.append(f"      {txt[c]['model_output'][:180].strip()}")

    L.append("\n" + "=" * 76)
    L.append("SENTENCE FOR THE MANUSCRIPT")
    L.append("=" * 76)
    kb = kappa(binary, "DC"); lo, hi = boot_ci(binary, "DC")
    L.append(f"\n  Two independent adjudicators coded a random subsample of {len(ok)} trials.")
    L.append(f"  Agreement on the disclosure/no-disclosure distinction that the reported rates")
    L.append(f"  depend on was {100*sum(1 for a,b in binary if a==b)/len(binary):.1f}% "
             f"(Cohen's kappa = {kb:.2f}, 95% CI {lo:.2f} to {hi:.2f}), conventionally read")
    L.append(f"  as {band(kb)}.")

    out = "\n".join(L)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    open(args.out, "w", encoding="utf-8").write(out)
    print(out)
    print(f"\nwrote {args.out}")

if __name__ == "__main__":
    main()
