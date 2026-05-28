# meta-starter-kit

Build a complete, offline meta-analysis web page from a small JSON file —
**no internet, no R, no pip install, no statistics knowledge required at
build time.** Designed for low-bandwidth / low-API-quota settings: the
heavy lifting (random-effects pooling, forest plot, page layout) is already
written and tested, so an AI CLI (or a person) only fills in the trial
numbers.

---

## ⬇️ Download (one click)

**[Click here to download the whole kit as a ZIP »](https://github.com/mahmood726-cyber/meta-starter-kit/archive/refs/heads/main.zip)**

Then unzip it. That's everything you need. (You can also get versioned
downloads on the [Releases page](https://github.com/mahmood726-cyber/meta-starter-kit/releases).)

## ▶️ Use it in 3 steps

1. **Install Python** (once) if you don't have it: <https://www.python.org/downloads/>
   — during install on Windows, tick **"Add Python to PATH"**.
2. **Run the example.**
   - **Windows:** double-click **`RUN_EXAMPLE.bat`**.
   - **Mac/Linux:** run `bash run_example.sh` in the unzipped folder.
   - **Any system (terminal):** `python build.py configs/example_finerenone_ckd.json`
3. **Open the result** — the file `output/example_finerenone_ckd.html` —
   in any web browser (the launcher opens it for you). Done: a full
   meta-analysis with a forest plot.

To make your **own** review, copy a file in `configs/`, put your trial
numbers in, and run `python build.py configs/your_file.json`. See
[Make your own](#make-your-own) below.

> No internet needed after download. Nothing to install except Python.
> Works on Windows, Mac, and Linux.

---

## Why this exists

Generating a full meta-analysis dashboard from scratch with an LLM burns a
lot of tokens and hits free-tier rate limits fast. Here the engine is
pre-built. The only thing that changes per review is a ~15-line config, so a
free Gemini/Claude CLI key can produce many reviews without exhausting quota.

## Requirements

- Python 3.8+ (standard library only — nothing to install)
- Any web browser to view the result

Check Python:
```
python --version
```

## Quick start (60 seconds)

```
python build.py configs/example_finerenone_ckd.json
```
Open `output/example_finerenone_ckd.html` in a browser. Done — that is a full
random-effects meta-analysis with a forest plot, heterogeneity statistics,
prediction interval, and a trial table.

## Make your own

1. Copy an example:
   ```
   copy configs\example_finerenone_ckd.json configs\my_review.json   (Windows)
   cp   configs/example_finerenone_ckd.json configs/my_review.json   (Mac/Linux)
   ```
2. Edit `configs/my_review.json` — change the title/PICO and put your trials in.
3. Build:
   ```
   python build.py configs/my_review.json
   ```
4. Open `output/my_review.html`.

### Two ways to give trial data

**A. Event counts (binary outcome)** — use `effect_measure: "OR"`:
```json
{ "name": "TRIAL-1", "nct": "NCT01234567", "year": 2020,
  "tE": 50, "tN": 500, "cE": 70, "cN": 500 }
```
`tE/tN` = events/total in the intervention arm, `cE/cN` = comparator arm.

**B. Published effect + 95% CI** — use `effect_measure` of `HR`, `RR`, `MD`,
`RD`, or `SMD`:
```json
{ "name": "TRIAL-1", "nct": "NCT...", "year": 2021,
  "effect": 0.82, "ci_low": 0.71, "ci_high": 0.95 }
```
Give ratios (HR/RR/OR) on the natural scale (0.82); give differences (MD/RD)
as the raw number (-10.2). See `configs/example_semaglutide_md.json`.

## What you get

- **Forest plot** — inline SVG, prints and works offline.
- **Random-effects pool** — Paule–Mandel τ², Knapp–Hartung confidence
  interval with a variance floor (so low-heterogeneity pools aren't given
  falsely narrow CIs), pooled estimate + 95% CI.
- **Prediction interval** — Cochrane Handbook v6.5 t(k−1) convention
  (shown only when k ≥ 3, where it is defined).
- **Heterogeneity** — I², τ², Cochran Q with p-value.
- **Trial table** — per-study estimate, CI, and weight.
- A plain-language one-line interpretation and a "verify against source"
  disclaimer.

## Methodology notes

- Binary outcomes are pooled as log odds ratios; a 0.5 continuity correction
  is added to all cells of a trial **only** when that trial has a zero cell.
- Ratio measures (OR/HR/RR) are pooled on the log scale and back-transformed.
- τ² uses Paule–Mandel (robust for the small numbers of trials typical here;
  Cochrane recommends REML or PM over DerSimonian–Laird for k < 10).
- The Knapp–Hartung interval uses a floor at 1 (Wiksten 2016) so that
  Q < k−1 cannot produce an interval narrower than the random-effects model
  justifies.

## What NOT to edit

`metakit/` (engine, forest, render) and `build.py` are finished. You should
only ever create/edit files in `configs/`. If a build fails it prints a
`[CONFIG ERROR]` naming exactly what to fix.

## Files

```
build.py                     run this: python build.py configs/<file>.json
metakit/engine.py            pooling math (do not edit)
metakit/forest.py            SVG forest plot (do not edit)
metakit/render.py            HTML assembly (do not edit)
configs/example_*.json       worked examples — copy these
output/                      built pages land here
schema.json                  config schema (for editor validation)
AGENTS.md / GEMINI.md        instructions for AI CLIs
```

## Honesty

Every page is an **auto-generated draft**. The kit does the arithmetic; it
cannot judge whether the trials are clinically combinable, whether the
extracted numbers are correct, or whether publication bias is present. Always
verify the inputs against the source papers and apply judgement before using
or citing any result.
