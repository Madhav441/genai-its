#!/usr/bin/env python3
"""Cross-model, full-corpus analysis of the adversarial robustness evaluation.

Reads one or more raw_results.csv files (one per model run), and emits:
  results_cross/cross_model_summary.csv   per model x family breach rates + Wilson CIs + McNemar
  results_cross/cross_model_table.tex     LaTeX table ready to paste into the manuscript
  results_cross/cross_model_report.txt    human-readable summary with the sentences to quote

Usage
-----
  python3 analyse_cross_model.py \
      --run "llama-3.3-70b-versatile=results_llama70b/raw_results.csv" \
      --run "openai/gpt-oss-120b=results_gptoss120b/raw_results.csv" \
      --run "llama-3.1-8b-instant=results_llama8b/raw_results.csv"

If a run file already has a `model` column it is used; the label before '=' is
only a fallback for older files written before that column existed.
"""
import argparse, csv, math, os, collections

def wilson(x, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / den), min(1.0, (c + r) / den))

def mcnemar(b, c):
    """b = ungoverned breach & governed clean; c = the reverse. Continuity-corrected.

    Returns (chi2, p, p_str). math.erfc underflows to exactly 0.0 for chi2 beyond
    roughly 1500, and a p-value of 0 is not a meaningful quantity to report. Where
    that happens we fall back to a log-space bound via the Chernoff tail so the
    manuscript can state an honest upper bound instead.
    """
    if b + c == 0:
        return 0.0, 1.0, "1"
    chi = (abs(b - c) - 1) ** 2 / (b + c)
    p = math.erfc(math.sqrt(chi) / math.sqrt(2))
    if p > 0:
        return chi, p, f"{p:.3e}"
    # log10 of the normal tail 2*(1-Phi(z)) for large z
    z = math.sqrt(chi)
    log10p = (math.log10(2) - 0.5 * z * z / math.log(10)
              - math.log10(z * math.sqrt(2 * math.pi)))
    return chi, 0.0, f"<10^{{{int(math.floor(log10p))}}}"

FAMLABEL = {
    "direct_override": "Direct instruction override",
    "role_hijack": "Role / persona hijack",
    "rubric_exfil": "Rubric / system-prompt exfiltration",
    "indirect_injection": "Indirect injection (ingested content)",
    "encoding_obfuscation": "Encoding / obfuscation",
    "social_engineering": "Social engineering",
}

def load(spec):
    label, path = spec.split("=", 1)
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    for r in rows:
        r.setdefault("model", label)
        if not r.get("model"):
            r["model"] = label
    return label, rows

def paired(rows, fam=None):
    """Return (b, c, n_pairs, gov_breach, ung_breach, n_gov, n_ung)."""
    sel = [r for r in rows if fam is None or r["family"] == fam]
    g = {(r["item_id"], r["payload_id"]): int(r["breach"]) for r in sel if r["condition"] == "governed"}
    u = {(r["item_id"], r["payload_id"]): int(r["breach"]) for r in sel if r["condition"] == "ungoverned"}
    keys = set(g) & set(u)
    b = sum(1 for k in keys if u[k] == 1 and g[k] == 0)
    c = sum(1 for k in keys if g[k] == 1 and u[k] == 0)
    return b, c, len(keys), sum(g.values()), sum(u.values()), len(g), len(u)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True,
                    help='"label=path/to/raw_results.csv" (repeatable)')
    ap.add_argument("--outdir", default="results_cross")
    ap.add_argument("--common-items", action="store_true",
                    help="restrict every run to the items covered by ALL runs (fair cross-model comparison)")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    runs = [load(s) for s in args.run]
    if args.common_items and len(runs) > 1:
        common = set.intersection(*[{r['item_id'] for r in rows} for _, rows in runs])
        runs = [(lab, [r for r in rows if r['item_id'] in common]) for lab, rows in runs]
        print(f'[--common-items] restricted to {len(common)} items covered by all runs')
    out = []
    csv_rows = []

    out.append("=" * 78)
    out.append("CROSS-MODEL ADVERSARIAL ROBUSTNESS SUMMARY")
    out.append("=" * 78)

    for label, rows in runs:
        model = rows[0]["model"] if rows else label
        fams = [f for f in FAMLABEL if any(r["family"] == f for r in rows)]
        b, c, npairs, gb, ub, ng, nu = paired(rows)
        glo, ghi = wilson(gb, ng)
        ulo, uhi = wilson(ub, nu)
        chi, p, pstr = mcnemar(b, c)
        out.append(f"\nMODEL: {model}")
        out.append(f"  paired trials per condition : {npairs}")
        out.append(f"  governed breaches           : {gb}/{ng} = {100*gb/max(1,ng):.1f}%  "
                   f"(95% CI {100*glo:.1f} to {100*ghi:.1f}%)")
        out.append(f"  ungoverned breaches         : {ub}/{nu} = {100*ub/max(1,nu):.1f}%  "
                   f"(95% CI {100*ulo:.1f} to {100*uhi:.1f}%)")
        out.append(f"  McNemar (b={b}, c={c})       : chi2={chi:.1f}  p={pstr}")
        csv_rows.append(dict(model=model, family="OVERALL", n_pairs=npairs,
                             gov_breach=gb, gov_n=ng, gov_pct=round(100*gb/max(1,ng), 2),
                             gov_ci_lo=round(100*glo, 2), gov_ci_hi=round(100*ghi, 2),
                             ung_breach=ub, ung_n=nu, ung_pct=round(100*ub/max(1,nu), 2),
                             ung_ci_lo=round(100*ulo, 2), ung_ci_hi=round(100*uhi, 2),
                             mcnemar_chi2=round(chi, 2), mcnemar_p=pstr))
        out.append("  by family:")
        for f in fams:
            b, c, npair, gb, ub, ng, nu = paired(rows, f)
            glo, ghi = wilson(gb, ng); ulo, uhi = wilson(ub, nu)
            chi, p, pstr = mcnemar(b, c)
            out.append(f"    {FAMLABEL[f]:38s} gov {100*gb/max(1,ng):5.1f}%  "
                       f"ung {100*ub/max(1,nu):5.1f}%  p={pstr}  (n={npair})")
            csv_rows.append(dict(model=model, family=f, n_pairs=npair,
                                 gov_breach=gb, gov_n=ng, gov_pct=round(100*gb/max(1,ng), 2),
                                 gov_ci_lo=round(100*glo, 2), gov_ci_hi=round(100*ghi, 2),
                                 ung_breach=ub, ung_n=nu, ung_pct=round(100*ub/max(1,nu), 2),
                                 ung_ci_lo=round(100*ulo, 2), ung_ci_hi=round(100*uhi, 2),
                                 mcnemar_chi2=round(chi, 2), mcnemar_p=pstr))

    # ---- CSV ----
    cpath = os.path.join(args.outdir, "cross_model_summary.csv")
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader(); w.writerows(csv_rows)

    # ---- LaTeX ----
    tex = [r"\begin{table}[!htbp]",
           r"  \caption{Adversarial robustness across models and attack families. "
           r"Governed and ungoverned conditions use the same items, payloads and model; "
           r"only the prompt contract differs. Breach rates are percentages with 95\% Wilson "
           r"intervals; $p$ from McNemar's test on paired item-payload outcomes.}",
           r"  \label{tab:redteam_crossmodel}", r"  \centering", r"  \footnotesize",
           r"  \renewcommand{\arraystretch}{1.2}",
           r"  \begin{tabular}{llccc}", r"    \toprule",
           r"    \textbf{Model} & \textbf{Attack family} & \textbf{Governed \%} "
           r"& \textbf{Ungoverned \%} & \textbf{McNemar $p$} \\", r"    \midrule"]
    for r in csv_rows:
        fam = "\\textbf{Overall}" if r["family"] == "OVERALL" else FAMLABEL.get(r["family"], r["family"])
        mdl = r["model"].replace("_", r"\_")
        gov = f"{r['gov_pct']:.1f} [{r['gov_ci_lo']:.1f}, {r['gov_ci_hi']:.1f}]"
        ung = f"{r['ung_pct']:.1f} [{r['ung_ci_lo']:.1f}, {r['ung_ci_hi']:.1f}]"
        tex.append(f"    \\texttt{{{mdl}}} & {fam} & {gov} & {ung} & ${r['mcnemar_p']}$ \\\\")
    tex += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    open(os.path.join(args.outdir, "cross_model_table.tex"), "w", encoding="utf-8").write("\n".join(tex))

    # ---- sentences to quote ----
    out.append("\n" + "=" * 78)
    out.append("SENTENCES YOU CAN QUOTE IN THE MANUSCRIPT")
    out.append("=" * 78)
    for r in [x for x in csv_rows if x["family"] == "OVERALL"]:
        out.append(f"\n  {r['model']}: the governed pipeline recorded {r['gov_breach']} breaches in "
                   f"{r['gov_n']} trials ({r['gov_pct']:.1f}%, 95% CI {r['gov_ci_lo']:.1f} to "
                   f"{r['gov_ci_hi']:.1f}%), against {r['ung_pct']:.1f}% ungoverned "
                   f"({r['ung_breach']}/{r['ung_n']}, CI {r['ung_ci_lo']:.1f} to {r['ung_ci_hi']:.1f}%); "
                   f"McNemar p = {r['mcnemar_p']}.")
    txt = "\n".join(out)
    open(os.path.join(args.outdir, "cross_model_report.txt"), "w", encoding="utf-8").write(txt)
    print(txt)
    print(f"\nwrote {cpath}")
    print(f"wrote {os.path.join(args.outdir,'cross_model_table.tex')}")
    print(f"wrote {os.path.join(args.outdir,'cross_model_report.txt')}")

if __name__ == "__main__":
    main()
