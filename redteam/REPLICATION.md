# Adversarial robustness evaluation: replication package

This directory contains the evaluation harness, attack corpus, and results underlying the
adversarial-robustness analysis reported in:

> Mukherjee, M., Le, J., & Chow, Y.-W. *Governance as a Security Control: Eliminating Solution
> Leakage and Prompt-Injection Risk in LLM-Based Cybersecurity Training.* Submitted to
> *Computers & Security*.

## What reproduces from this package

Running the checks below against `results/raw_results_redacted.csv` reproduces every figure in
the paper's adversarial-robustness table and surrounding text:

| Reported quantity | Value |
|---|---|
| Governed breach rate | 0.0% (0/240), Wilson 95% CI 0.0 to 1.6% |
| Ungoverned breach rate | 61.7% (148/240) |
| Overall McNemar | chi-square = 146.0, p = 1.3e-33 |
| Direct instruction override | 0.0% vs 65.0%, p = 9.4e-07 |
| Role / persona hijack | 0.0% vs 75.0%, p = 1.2e-07 |
| Rubric / system-prompt exfiltration | 0.0% vs 47.5%, p = 3.6e-05 |
| Indirect injection | 0.0% vs 65.0%, p = 9.4e-07 |
| Encoding / obfuscation | 0.0% vs 60.0%, p = 2.7e-06 |
| Social engineering | 0.0% vs 57.5%, p = 4.5e-06 |
| Borderline flags for adjudication | 14 |

## Contents

| File | Description |
|---|---|
| `redteam_run.py` | Evaluation harness. Runs each attack payload against each item under both prompt conditions. |
| `attack_corpus.csv` | Versioned attack corpus v1.0. 48 payloads across six OWASP-grounded families. |
| `items_template.csv` | Two synthetic example items showing the required input format. |
| `results/raw_results_redacted.csv` | Per-trial outcomes for all 480 trials. See redaction note below. |
| `results/summary_by_family.csv` | Aggregate breach rates and McNemar statistics per family. |
| `results/results_table.tex` | LaTeX table as it appears in the manuscript. |
| `results/coding_record_rater2.py` | Second automated coder's binary breach codes, keyed by row index. |
| `human_sheet_key.csv` | Maps blind coding IDs to trial index, condition, family, and automated label. |
| `make_human_sheet.py` | Generates a blinded coding sheet for independent human coding. |
| `score_human_kappa.py` | Scores returned human codes against the automated coders. |
| `verify_provenance.py` | Integrity check over the results files. |
| `fetch_items_firestore.py` | Utility for exporting an item bank from Firestore. Requires your own credentials. |

## Redactions and why

Two categories of material are deliberately withheld. Both withholdings are noted in the
manuscript's data-availability statement.

**1. The item bank (`items.csv`) is not included.**
The evaluation ran against 142 real assessment items drawn from two live postgraduate
cybersecurity subjects. Each row carries the question, the reference answer, and the
instructor-authored rubric. Publishing an answer key and rubric set for assessments still in
use would compromise the assessment integrity of those subjects, which is the precise failure
mode this paper argues against. Use `items_template.csv` to supply your own item bank in the
same format.

**2. The `output` column is removed from the raw results.**
The full model outputs include 148 ungoverned responses that disclosed complete worked
solutions to those same assessment items. Every other column is retained, so all reported
statistics remain independently checkable. Retained columns: `item_id`, `subject`, `family`,
`payload_id`, `condition`, `label`, `breach`, `answer_recall`, `needs_human_review`.

Researchers who need the withheld material for verification may request it from the
corresponding author, subject to the ethics and consent constraints of University of
Wollongong HREC approval 2024/218.

## Running the harness on your own item bank

```bash
# 1. Supply your items in the template format
cp items_template.csv items.csv    # then populate

# 2. Provide a model endpoint credential via a keyfile (never commit it)
printf '%s' 'YOUR_API_KEY' > .groq_key

# 3. Dry run with no key and no cost
python3 redteam_run.py --items items_template.csv --provider mock

# 4. Real run (open-model arm as reported in the paper)
python3 redteam_run.py --items items.csv --provider groq \
    --model llama-3.3-70b-versatile --keyfile .groq_key --sleep 2.0
```

`.gitignore` in this directory excludes credential files, the item bank, and raw run outputs.
Do not remove those entries.

## Human inter-rater reliability

The 38-trial verification subset was coded three times: by the automated recall heuristic, by
an LLM second coder, and by an independent human coder (a doctoral researcher not otherwise
involved in the study) working blind to the automated labels and to the experimental condition.

| Comparison | n | Agreement | Cohen's kappa |
|---|---|---|---|
| Human vs automated heuristic | 38 | 60.5% | 0.211 (95% CI -0.100 to 0.521) |
| Human vs LLM second coder | 38 | 68.4% | 0.380 (95% CI 0.090 to 0.670) |
| Governed condition only | 8 | 100% (8/8) | undefined; all three coders recorded zero breaches |
| Ungoverned condition only | 30 | 50% (15/30) | 0.051 |

The governed 0% breach rate is confirmed by all three coders independently. The ungoverned rate
is not reliably measured: the human recorded 12 breaches where the heuristic recorded 19 on the
same trials, so the 61.7% figure in the manuscript is an upper estimate produced by a liberal
automated criterion. The manuscript reports this openly and includes a sensitivity analysis
showing the governed-versus-ungoverned contrast holds across the plausible range.

`human_codes_redacted.csv` contains the human coder's per-trial breach codes with the question,
reference answer, and model output columns removed. `human_sheet_key.csv` maps each blind code
ID back to trial index, condition, and family. `results/reliability_report.txt` is the output of
`score_human_kappa.py` over those files.
