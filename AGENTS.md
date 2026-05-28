# AGENTS.md — instructions for AI CLIs (Gemini CLI, Claude Code, etc.)

You are helping someone build a **meta-analysis web page**. This repo is a
finished tool. Your job is **small and cheap**: write one short JSON config,
then run one command. Do **not** generate statistics code, HTML, or plots —
they already exist and are tested.

## The only workflow

1. Create a config file in `configs/` (copy `configs/example_finerenone_ckd.json`).
2. Fill in the trial data the user gives you.
3. Run: `python build.py configs/<their_file>.json`
4. The finished page appears in `output/<their_file>.html`. Open it in a browser.

That is the entire task. A typical config is 10–25 lines. **Do not** read or
edit anything in `metakit/` — it is the engine and it is complete.

## Token discipline (important on free/low-quota API keys)

- Writing the config is the ONLY text you need to generate. Keep it minimal.
- Never paste the engine, the template, or the built HTML back to the user.
- Never re-derive the statistics — `build.py` computes them deterministically
  with zero API calls.
- If the build prints a `[CONFIG ERROR]`, fix only the line it names. Don't
  rewrite the whole config.

## Config format

Two trial styles — pick whichever matches the data you were given.

### Style A — binary outcome (event counts), effect_measure "OR"

```json
{
  "title": "Drug X for outcome Y in condition Z",
  "intervention": "Drug X",
  "comparator": "Placebo",
  "condition": "the population",
  "outcome": "the primary outcome",
  "effect_measure": "OR",
  "trials": [
    { "name": "TRIAL-1", "nct": "NCT01234567", "year": 2020,
      "tE": 50, "tN": 500, "cE": 70, "cN": 500 }
  ]
}
```
`tE`/`tN` = events/total in the intervention arm; `cE`/`cN` = comparator arm.

### Style B — pre-computed effect + 95% CI (effect_measure "HR", "RR", "MD", "RD", "SMD")

```json
{
  "title": "...",
  "intervention": "...",
  "comparator": "...",
  "condition": "...",
  "outcome": "...",
  "effect_measure": "HR",
  "trials": [
    { "name": "TRIAL-1", "nct": "NCT...", "year": 2021,
      "effect": 0.82, "ci_low": 0.71, "ci_high": 0.95 }
  ]
}
```
For ratio measures (HR/RR/OR) give the natural-scale value (e.g. HR 0.82).
For difference measures (MD/RD/SMD) give the raw difference (e.g. -10.2).

## Rules

- Need **at least 2 trials** — a meta-analysis pools studies.
- Use real numbers from the source the user provides. Never invent trial data.
- `nct`, `year`, `pmid` are optional but helpful.
- One config = one outcome. For a second outcome, make a second config.
- The page footer already states it is an auto-generated draft to be verified
  against source publications — you do not need to add disclaimers.

## What the tool does for you (so you don't have to)

- Pooling: random-effects, Paule–Mandel τ², Knapp–Hartung CI with a floor,
  Cochrane v6.5 t(k−1) prediction interval.
- A forest plot (inline SVG, no internet needed).
- A clean, printable, fully-offline HTML page.

## Don't

- Don't `pip install` anything — the kit is pure standard-library Python 3.8+.
- Don't edit `metakit/`, `build.py`, or the CSS.
- Don't fetch from the internet to "improve" the page; it must work offline.
