#!/usr/bin/env python
"""Build a standalone meta-analysis HTML page from a small JSON config.

USAGE
    python build.py configs/your_review.json
    python build.py configs/your_review.json --out output/custom_name.html

This is the ONLY command you run. It is deterministic — it spends zero
network/LLM calls. Write a config (see README.md / configs/example_*.json),
run this, open the HTML.

The config tells the kit what trials to pool. Everything else (statistics,
forest plot, page layout) is already built in metakit/ and you should not
need to touch it.

Exit codes: 0 = built OK, 2 = bad config (message explains what to fix).
"""
from __future__ import annotations
import argparse
import json
import sys
import io
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from metakit import engine, forest, render  # noqa: E402

VALID_SCALES = {"OR", "HR", "RR", "MD", "SMD", "RD"}


def die(msg: str):
    print(f"\n[CONFIG ERROR] {msg}\n", file=sys.stderr)
    print("See README.md for the config format, or copy configs/example_finerenone_ckd.json.",
          file=sys.stderr)
    sys.exit(2)


def load_config(path: Path) -> dict:
    if not path.exists():
        die(f"config file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"config is not valid JSON: {e}")


def build_trials(cfg: dict, scale: str):
    """Turn config['trials'] into a list of engine.TrialEffect."""
    raw_trials = cfg.get("trials")
    if not isinstance(raw_trials, list) or len(raw_trials) < 2:
        die("config must have a 'trials' array with at least 2 trials "
            "(a meta-analysis needs >= 2 studies).")

    binary_mode = scale in engine.RATIO_SCALES and "tE" in raw_trials[0]
    effects = []
    for i, t in enumerate(raw_trials):
        name = t.get("name") or t.get("nct") or f"Trial {i+1}"
        meta = {"nct": t.get("nct"), "year": t.get("year"), "pmid": t.get("pmid")}
        if all(k in t for k in ("tE", "tN", "cE", "cN")):
            eff = engine.binary_effect(
                name, int(t["tE"]), int(t["tN"]), int(t["cE"]), int(t["cN"]), **meta)
            if eff is None:
                print(f"  [skip] {name}: unusable 2x2 table "
                      f"(tE={t['tE']} tN={t['tN']} cE={t['cE']} cN={t['cN']})")
                continue
        elif all(k in t for k in ("effect", "ci_low", "ci_high")):
            eff = engine.precomputed_effect(
                name, float(t["effect"]), float(t["ci_low"]),
                float(t["ci_high"]), scale, **meta)
            if eff is None:
                print(f"  [skip] {name}: unusable effect+CI "
                      f"(effect={t['effect']} ci=[{t['ci_low']},{t['ci_high']}])")
                continue
        else:
            die(f"trial {i+1} ('{name}') needs either binary counts "
                "(tE,tN,cE,cN) or a precomputed effect (effect,ci_low,ci_high).")
        effects.append(eff)

    if len(effects) < 2:
        die(f"after dropping unusable trials only {len(effects)} remain; "
            "need >= 2 to pool.")
    return effects


def main():
    ap = argparse.ArgumentParser(description="Build a meta-analysis page from a config JSON.")
    ap.add_argument("config", help="path to the config JSON (e.g. configs/my_review.json)")
    ap.add_argument("--out", help="output HTML path (default: output/<config-stem>.html)")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg = load_config(cfg_path)

    scale = (cfg.get("effect_measure") or "OR").upper()
    if scale not in VALID_SCALES:
        die(f"effect_measure '{scale}' is not one of {sorted(VALID_SCALES)}.")

    if not cfg.get("title"):
        die("config needs a 'title'.")

    effects = build_trials(cfg, scale)
    pool = engine.pool_effects(effects, scale)
    if pool is None:
        die("pooling failed (need >= 2 usable trials).")

    svg = forest.forest_svg(
        pool, scale,
        intervention=cfg.get("intervention", "Intervention"),
        comparator=cfg.get("comparator", "Comparator"),
    )
    html_doc = render.render_html(cfg, pool, svg, scale)

    out_path = Path(args.out) if args.out else (HERE / "output" / f"{cfg_path.stem}.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")

    ratio = scale in engine.RATIO_SCALES
    print(f"\nBuilt: {out_path}")
    print(f"  {pool.k} trials pooled · {scale} = {pool.pooled:.3f} "
          f"(95% CI {pool.ci_low:.3f} to {pool.ci_high:.3f})")
    print(f"  I2 = {pool.i2:.1f}%  tau2 = {pool.tau2:.4f}  Q-p = {pool.Q_p:.4g}")
    if pool.pi_low is not None:
        print(f"  95% prediction interval: {pool.pi_low:.3f} to {pool.pi_high:.3f}")
    print(f"\nOpen the file in any browser (works offline).")


if __name__ == "__main__":
    main()
