#!/usr/bin/env python3
"""Reproduce the adjudicated disclosure rates, protection ratios and their cluster-bootstrap
intervals reported in Table 5 and Section 5.2 of the revised manuscript, from the released files only.

    python3 bootstrap_intervals.py            # item-clustered (Table 5) and payload-clustered intervals
Requires: pandas, numpy.  Uses: results/raw_results_redacted.csv, adjudication/governed_codes.csv,
adjudication/ungoverned_codes.csv.  The item whose reference answer is itself a refusal is excluded,
as in the paper (141 items, 6,768 trials per model per condition).
"""
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
REFUSAL_ITEM = "COMP804_Week 9#4"
B, SEED = 4000, 20261108

raw = pd.read_csv(os.path.join(HERE, "results", "raw_results_redacted.csv"))
raw = raw[raw.item_id != REFUSAL_ITEM]
codes = {c: pd.read_csv(os.path.join(HERE, "adjudication", f"{c}_codes.csv")) for c in ("governed", "ungoverned")}
for k in codes.values():
    k["disc"] = k.adjudicated_code.isin(["A", "B"]).astype(int)          # A = solution, B = rubric disclosure
    k["st"] = np.where(k.stratum.str.startswith("A"), 0, 1)             # 0 = flagged stratum, 1 = clean stratum
MODELS = sorted(raw.model.unique())

def arrays(cluster):
    units = np.array(sorted(raw[cluster].unique())); ix = {u: i for i, u in enumerate(units)}; U = len(units)
    F = np.zeros((2, 3, U)); T = np.zeros((2, 3, U)); S = np.zeros((2, 3, 2, U)); N = np.zeros((2, 3, 2, U))
    for ci, cond in enumerate(("governed", "ungoverned")):
        for mi, m in enumerate(MODELS):
            g = raw[(raw.condition == cond) & (raw.model == m)].groupby(cluster).breach.agg(["sum", "size"])
            for u, row in g.iterrows(): F[ci, mi, ix[u]], T[ci, mi, ix[u]] = row["sum"], row["size"]
            k = codes[cond]; k = k[k.model == m]
            for si in (0, 1):
                a = k[k.st == si].groupby(cluster).disc.agg(["sum", "size"])
                for u, row in a.iterrows(): S[ci, mi, si, ix[u]], N[ci, mi, si, ix[u]] = row["sum"], row["size"]
    return U, F, T, S, N

def estimate(w, F, T, S, N):
    out = np.zeros((2, 4))
    for ci in range(2):
        tot = den = 0.0
        for mi in range(3):
            f = (F[ci, mi] * w).sum(); t = (T[ci, mi] * w).sum()
            na, nb = (N[ci, mi, 0] * w).sum(), (N[ci, mi, 1] * w).sum()
            pa = (S[ci, mi, 0] * w).sum() / na if na > 0 else 0.0
            pb = (S[ci, mi, 1] * w).sum() / nb if nb > 0 else 0.0
            e = f * pa + (t - f) * pb; out[ci, mi] = e / t; tot += e; den += t
        out[ci, 3] = tot / den
    return out

names = MODELS + ["pooled"]
for cluster in ("item_id", "payload_id"):
    U, F, T, S, N = arrays(cluster)
    pt = estimate(np.ones(U), F, T, S, N)
    rng = np.random.default_rng(SEED)
    bs = np.array([estimate(np.bincount(rng.integers(0, U, U), minlength=U).astype(float), F, T, S, N) for _ in range(B)])
    print(f"\n{cluster}-clustered bootstrap, {B} replicates, 95% percentile intervals")
    for j, nm in enumerate(names):
        g = np.percentile(bs[:, 0, j], [2.5, 97.5]) * 100; u = np.percentile(bs[:, 1, j], [2.5, 97.5]) * 100
        r = np.nanpercentile(bs[:, 1, j] / np.where(bs[:, 0, j] > 0, bs[:, 0, j], np.nan), [2.5, 97.5])
        print(f"  {nm:26s} governed {100*pt[0,j]:5.1f} [{g[0]:.1f}, {g[1]:.1f}]   ungoverned {100*pt[1,j]:5.1f} [{u[0]:.1f}, {u[1]:.1f}]   ratio {pt[1,j]/pt[0,j]:.1f} [{r[0]:.1f}, {r[1]:.1f}]")
gov = raw[raw.condition == "governed"]
print("\nAutomated governed flag rate (141 items): " + ", ".join(f"{m} {100*gov[gov.model==m].breach.mean():.2f}%" for m in MODELS)
      + f"; pooled {100*gov.breach.mean():.2f}% ({int(gov.breach.sum())} flags)")
