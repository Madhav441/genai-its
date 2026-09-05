# GenAITS red-team harness

Adversarial-robustness evaluation of the GenAITS governed tutoring pipeline: does a bounded
prompt contract stop an LLM tutor disclosing assessment solutions when a learner actively
attacks it?

**Start with [`REPLICATION.md`](REPLICATION.md).** It states the design, what reproduces from
this package, what is withheld and why, and how to re-run the evaluation on your own item
bank.

## Scale

142 assessment items x 6 attack families x 8 payloads x 2 conditions x 3 open-weight models
= 40,896 paired trials. Models: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`,
`openai/gpt-oss-120b`.

## Result in short

Automated recall-based coding put governed disclosure at 0.2% pooled. Blind human
adjudication of two sampled strata put it at 21.2% (95% CI 15.8 to 26.5) against 57.8%
ungoverned. The automated coder had acceptable precision, 88% to 100%, but recall under 1.4%
against subtle disclosure, so the near-zero reading was an artefact of the instrument rather
than a property of the system.

The residual channel is not attack success. The contract requires the model to name each
unmet rubric criterion, and naming a criterion frequently names the answer. Protection also
varies sharply by model under an identical contract, from roughly tenfold to none.

If you are evaluating a guardrail of this kind, the practical lesson is that recall-based
automated scoring will report a rate close to zero regardless of what the system is actually
doing, and that measuring only whether attacks are deflected will miss disclosure that flows
through the compliant path.

## Layout

```
redteam/
  REPLICATION.md              full replication guide, start here
  redteam_run.py              evaluation harness
  attack_corpus.csv           versioned attack corpus v1.0, 48 payloads
  items_template.csv          synthetic schema example, not the real item bank
  analyse_cross_model.py      automated rates, Wilson intervals, McNemar
  make_stratified_adjudication.py / score_stratified_adjudication.py
  score_reliability.py        inter-rater kappa
  results/                    per-trial outcomes and precomputed reports
  adjudication/               adjudicator codes and sampling keys
  coding_instruments/         coding rules as issued to adjudicators
```

## Quick start

```bash
python3 redteam_run.py --items items_template.csv --provider mock   # no key, no cost
```

## Withheld material

The 142-item bank and the raw model-output column are deliberately not published, because
between them they constitute an answer key for assessments still in use. Everything needed to
recompute every reported statistic is included. See `REPLICATION.md` for the full statement
and the contact route for verification access.

## Licence

MIT, see [`../LICENSE`](../LICENSE). Copyright (c) 2026 Madhav Mukherjee, John Le, and
Yang-Wai Chow.
