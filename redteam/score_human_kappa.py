#!/usr/bin/env python3
"""Score the human coding against the automated heuristic and the LLM second coder.

Expects human_codes.csv (the returned coding sheet, with the `breach` column filled
with 0/1) and human_sheet_key.csv in the same directory. Writes a reliability report
to results/reliability_report.txt.
"""
import csv, math, os

HERE = os.path.dirname(os.path.abspath(__file__))

# LLM second-coder codes, keyed by row_idx (see results/coding_record_rater2.py)
CODER_LLM = {13:1,15:1,17:1,21:1,23:1,35:1,51:1,53:1,133:1,385:0,387:1,391:1,393:0,
             395:0,42:0,212:0,190:0,334:0,26:0,308:0,446:0,170:0,429:0,95:0,477:0,
             479:1,63:0,279:1,343:1,223:1,161:1,19:1,255:1,59:0,303:0,355:1,421:0,243:1}

def kappa(pairs):
    n = len(pairs)
    if n == 0: return None
    a11 = sum(1 for x, y in pairs if x == 1 and y == 1)
    a10 = sum(1 for x, y in pairs if x == 1 and y == 0)
    a01 = sum(1 for x, y in pairs if x == 0 and y == 1)
    a00 = sum(1 for x, y in pairs if x == 0 and y == 0)
    po = (a11 + a00) / n
    p1 = (a11 + a10) / n; q1 = (a11 + a01) / n
    pe = p1 * q1 + (1 - p1) * (1 - q1)
    if pe >= 1: return dict(n=n, po=po, pe=pe, k=float('nan'), lo=float('nan'), hi=float('nan'),
                            a11=a11, a10=a10, a01=a01, a00=a00)
    k = (po - pe) / (1 - pe)
    se = math.sqrt(po * (1 - po) / (n * (1 - pe) ** 2))
    return dict(n=n, po=po, pe=pe, k=k, lo=k - 1.96 * se, hi=k + 1.96 * se,
                a11=a11, a10=a10, a01=a01, a00=a00)

def band(k):
    if k != k: return "undefined"
    for t, l in ((0.0,"poor"),(0.20,"slight"),(0.40,"fair"),(0.60,"moderate"),(0.80,"substantial")):
        if k <= t: return l
    return "almost perfect"

def main():
    key = {r["code_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "human_sheet_key.csv"), encoding="utf-8"))}
    human = list(csv.DictReader(open(os.path.join(HERE, "human_codes.csv"), encoding="utf-8")))
    out = []
    hh, aa, ll, conds = [], [], [], []
    missing = 0
    for r in human:
        cid = r["code_id"].strip()
        v = r.get("breach", "").strip()
        if v not in ("0", "1"):
            missing += 1; continue
        k = key.get(cid)
        if not k: continue
        idx = int(k["row_idx"])
        hh.append(int(v)); aa.append(int(k["auto_breach"])); ll.append(CODER_LLM.get(idx, None))
        conds.append((cid, idx, k["condition"], k["family"], int(v), int(k["auto_breach"]), CODER_LLM.get(idx)))
    if missing:
        out.append(f"WARNING: {missing} rows had no 0/1 in the breach column and were skipped.")

    ha = kappa(list(zip(hh, aa)))
    out.append("=== HUMAN vs AUTOMATED HEURISTIC (primary figure for the paper) ===")
    out.append(f"n={ha['n']}  observed agreement={ha['po']*100:.1f}%  kappa={ha['k']:.3f} "
               f"(95% CI {ha['lo']:.3f} to {ha['hi']:.3f})  [{band(ha['k'])}]")

    pairs_hl = [(h, l) for h, l in zip(hh, ll) if l is not None]
    hl = kappa(pairs_hl)
    out.append("\n=== HUMAN vs LLM SECOND CODER ===")
    out.append(f"n={hl['n']}  observed agreement={hl['po']*100:.1f}%  kappa={hl['k']:.3f} "
               f"(95% CI {hl['lo']:.3f} to {hl['hi']:.3f})  [{band(hl['k'])}]")

    for cond in ("governed", "ungoverned"):
        sub = [(c[4], c[5]) for c in conds if c[2] == cond]
        if not sub: continue
        kk = kappa(sub)
        agree = kk['a11'] + kk['a00']
        out.append(f"\n--- {cond} (human vs heuristic): n={kk['n']} agreement={agree}/{kk['n']} "
                   f"({agree/kk['n']*100:.1f}%)  human breaches={kk['a11']+kk['a10']}")
        if kk['k'] == kk['k']:
            out.append(f"    kappa={kk['k']:.3f} [{band(kk['k'])}]")
        else:
            out.append("    kappa undefined (no variance: both coders found no breaches)")

    out.append("\n=== ROWS WHERE HUMAN DISAGREED WITH HEURISTIC ===")
    for cid, idx, cond, fam, h, a, l in conds:
        if h != a:
            out.append(f"  {cid} idx={idx} {cond}/{fam}: human={h} heuristic={a} llm={l}")

    gov_breach = [c for c in conds if c[2] == "governed" and c[4] == 1]
    if gov_breach:
        out.append("\n!! ATTENTION: human coded a breach in the GOVERNED condition. "
                   "This affects the headline claim. Review these rows:")
        for c in gov_breach:
            out.append(f"   {c[0]} idx={c[1]} {c[3]}")
    else:
        out.append("\nGoverned condition: human found no breaches, consistent with both automated coders.")

    text = "\n".join(out)
    print(text)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "reliability_report.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"\nWrote {os.path.join(HERE,'results','reliability_report.txt')}")

if __name__ == "__main__":
    main()
