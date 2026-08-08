# GenAITS red-team harness

Automates the adversarial-robustness evaluation (OWASP LLM01) described in
`../GenAITS_RedTeam_Protocol.md`. Measures prompt-injection **breach rate** under
governed vs ungoverned feedback prompts. Stdlib-only Python 3 (no pip installs).

## What you need to supply (only 3 things)

1. **A model API key.** GroqCloud is supported (OpenAI-compatible). Note Groq serves
   *open* models (Llama, Mixtral, Gemma, Qwen), not GPT-4, so a Groq run is the
   open-model arm of the evaluation and should be described as such in the paper; it
   is not directly comparable to the paper's GPT-4 cooperative-input result. The same
   harness also runs against OpenAI or Anthropic if you later want a commercial-model
   arm.
2. **`items.csv`** — your 40-item corpus, one row per question, columns:
   `item_id, subject, question, correct_answer, rubric`. Copy the format in
   `items_template.csv` and export from your GitHub repo / Firestore. Use the same
   40 items as the paper's feedback-security comparison for comparability.
3. **Which model(s)** to run. Single model = solid; add a second commercial and one
   open (Ollama) model = the cross-model robustness contribution.

Everything else (attack corpus, prompts, running, grading, stats, LaTeX table) is done.

## Handle the key safely

Do NOT paste the key into chat or hard-code it. Put it in a file the script reads:

```bash
printf '%s' 'YOUR_GROQ_KEY' > .groq_key      # .groq_key is already in .gitignore
```

The `--keyfile` flag loads it into the right environment variable at runtime and it
is never printed or committed.

## Run it

```bash
# prove it runs first (no key, no cost):
python3 redteam_run.py --items items_template.csv --provider mock

# real run on GroqCloud (open-model arm):
python3 redteam_run.py --items items.csv --provider groq \
    --model llama-3.3-70b-versatile --keyfile .groq_key --sleep 2.0

# other providers if ever needed:
#   --provider openai    --model gpt-4                       (env OPENAI_API_KEY or --keyfile)
#   --provider anthropic --model claude-sonnet-4-20250514    (env ANTHROPIC_API_KEY or --keyfile)
#   --provider ollama    --model mistral                     (local, free, no key)
```

Cost/limits: 40 items x 48 attacks x 2 conditions = 3,840 calls per model. Groq's
free tier is rate-limited (about 30 requests/min on Llama 3.3 70B), so use
`--sleep 2.0` to stay under it; a paid tier can go faster. Groq inference is cheap
relative to GPT-4.

## Outputs (in `results/`)

- `raw_results.csv` — every call: label, breach flag, answer-recall, truncated output,
  and a `needs_human_review` flag for borderline cases.
- `summary_by_family.csv` — breach/rubric-leak rates and McNemar per attack family.
- `results_table.tex` — paste straight into the manuscript as Table `tab:redteam`.

## Grading and the human-validation step

The auto-grader labels each output `full_leak / partial_leak / rubric_leak / clean`
using answer-token recall + leakage heuristics, and flags borderline items
(`needs_human_review=1`). For the paper, have a second person hand-code the flagged
subset (plus a random ~50) and report Cohen's kappa — this doubles as the
"independent human-rater validation" already promised in the manuscript. Tune the
grader thresholds in `grade()` if your answers are very short or very long.

## Then

Paste `results_table.tex` into Results, add one sentence to the abstract and
conclusion converting the "red-team pending" note into a measured result, and
retire (or narrow to cross-model) future-work item 4.
