# GEMINI.md

Gemini CLI: read **[AGENTS.md](AGENTS.md)** — it is the full and authoritative
guide for this repo. Everything you need is there.

One-paragraph summary so you don't spend tokens re-reading:

> This is a finished meta-analysis builder. To make a new review, copy
> `configs/example_finerenone_ckd.json`, replace the trial data with the
> user's numbers, and run `python build.py configs/<file>.json`. The page
> lands in `output/`. Do **not** edit `metakit/` or `build.py` — the
> statistics, forest plot, and HTML are already done. Keep your output to
> just the small config JSON; the build is deterministic and uses no API
> calls, which conserves your quota.
