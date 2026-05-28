"""Assemble a complete, standalone meta-analysis HTML document.

All values are computed at build time (Python), so the output page is
small, loads instantly, works fully offline, and needs no client-side
statistics engine. Finished — not edited per-review.

Guards against the Python-None-into-HTML leak class (lessons.md): every
interpolated value passes through _h()/_num() which map None to an
explicit em-dash, never the literal token "None".
"""
from __future__ import annotations
import html
import math
from .engine import RATIO_SCALES, per_trial_display

SCALE_NAMES = {
    "OR": "Odds ratio", "HR": "Hazard ratio", "RR": "Risk ratio",
    "MD": "Mean difference", "SMD": "Standardised mean difference",
    "RD": "Risk difference",
}


def _h(s) -> str:
    if s is None:
        return "&mdash;"
    return html.escape(str(s))


def _num(v, nd=2) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "&mdash;"
    return f"{v:.{nd}f}"


def _interpret(pool, scale) -> str:
    ratio = scale in RATIO_SCALES
    null = 1.0 if ratio else 0.0
    crosses = pool.ci_low <= null <= pool.ci_high
    if crosses:
        direction = "no statistically significant difference"
    elif (ratio and pool.pooled < 1) or (not ratio and pool.pooled < 0):
        direction = "a statistically significant benefit of the intervention"
    else:
        direction = "a statistically significant effect favouring the comparator"
    het = ("low" if pool.i2 < 30 else "moderate" if pool.i2 < 60
           else "substantial" if pool.i2 < 75 else "considerable")
    return (f"Across {pool.k} trials the random-effects pool shows {direction} "
            f"({SCALE_NAMES.get(scale, scale)} {_num(pool.pooled)}, "
            f"95% CI {_num(pool.ci_low)} to {_num(pool.ci_high)}). "
            f"Between-study heterogeneity is {het} (I&sup2; {_num(pool.i2, 1)}%).")


def render_html(config: dict, pool, forest_svg: str, scale: str) -> str:
    title = _h(config.get("title") or "Meta-analysis")
    intervention = _h(config.get("intervention") or "Intervention")
    comparator = _h(config.get("comparator") or "Comparator")
    condition = _h(config.get("condition") or "")
    outcome = _h(config.get("outcome") or "")
    authors = _h(config.get("authors") or "")
    scale_name = SCALE_NAMES.get(scale, scale)
    ratio = scale in RATIO_SCALES

    # Trial table rows
    rows = []
    for i, t in enumerate(pool.trials):
        p, lo, hi = per_trial_display(t, scale)
        raw = t.raw
        if "tE" in raw:
            data_cell = (f'{raw["tE"]}/{raw["tN"]} vs {raw["cE"]}/{raw["cN"]}')
        else:
            data_cell = (f'{_num(raw.get("effect"))} '
                         f'({_num(raw.get("ci_low"))}, {_num(raw.get("ci_high"))})')
        rows.append(
            f"<tr><td>{_h(t.name)}</td>"
            f"<td class='mono'>{_h(t.nct) if t.nct else '&mdash;'}</td>"
            f"<td class='num'>{_h(t.year) if t.year else '&mdash;'}</td>"
            f"<td class='num'>{data_cell}</td>"
            f"<td class='num'>{_num(p)} ({_num(lo)}, {_num(hi)})</td>"
            f"<td class='num'>{_num(pool.weights_pct[i], 1)}%</td></tr>"
        )
    trial_rows = "\n".join(rows)

    pi_cell = (f"{_num(pool.pi_low)} to {_num(pool.pi_high)}"
               if pool.pi_low is not None else "undefined (k&lt;3)")
    floor_note = (" (HKSJ variance floor applied — Wiksten 2016)"
                  if pool.hksj_floor_applied else "")
    qp = pool.Q_p
    qp_fmt = (f"{qp:.3f}" if qp == qp and qp >= 0.001 else
              f"{qp:.2e}" if qp == qp else "&mdash;")

    interpretation = _interpret(pool, scale)
    null_val = "1.0" if ratio else "0.0"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{title} — random-effects meta-analysis ({scale_name})">
<style>
  :root {{ --ink:#1e293b; --muted:#64748b; --line:#e2e8f0; --accent:#2563eb; --bg:#f8fafc; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font-family:system-ui,-apple-system,sans-serif; line-height:1.55; }}
  header {{ background:#0f172a; color:#fff; padding:28px 24px; }}
  header h1 {{ margin:0 0 6px; font-size:22px; }}
  header .pico {{ color:#cbd5e1; font-size:13px; }}
  main {{ max-width:880px; margin:0 auto; padding:24px; }}
  section {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:20px 22px; margin-bottom:18px; }}
  h2 {{ font-size:15px; margin:0 0 12px; color:#0f172a; }}
  .headline {{ font-size:16px; line-height:1.6; }}
  .kpis {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:8px; }}
  .kpi {{ background:var(--bg); border:1px solid var(--line); border-radius:6px; padding:10px 14px; min-width:120px; }}
  .kpi .v {{ font-size:20px; font-weight:600; color:var(--accent); }}
  .kpi .l {{ font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:0.04em; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); }}
  th {{ background:var(--bg); font-size:12px; }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  td.mono {{ font-family:ui-monospace,monospace; font-size:11px; }}
  .forest {{ overflow-x:auto; }}
  .forest svg {{ max-width:100%; height:auto; border:1px solid var(--line); border-radius:6px; }}
  .meta-note {{ font-size:12px; color:var(--muted); }}
  .disclaimer {{ background:#fffbeb; border:1px solid #fde68a; color:#92400e; border-radius:6px; padding:12px 16px; font-size:12px; }}
  footer {{ max-width:880px; margin:0 auto; padding:0 24px 32px; color:var(--muted); font-size:11px; }}
  code {{ background:var(--bg); padding:1px 5px; border-radius:3px; font-size:12px; }}
  a {{ color:var(--accent); }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="pico">
    <strong>Population:</strong> {condition or "&mdash;"} &nbsp;·&nbsp;
    <strong>Intervention:</strong> {intervention} &nbsp;·&nbsp;
    <strong>Comparator:</strong> {comparator} &nbsp;·&nbsp;
    <strong>Outcome:</strong> {outcome or "&mdash;"}
  </div>
</header>
<main>

  <section>
    <h2>Result</h2>
    <p class="headline">{interpretation}</p>
    <div class="kpis">
      <div class="kpi"><div class="v">{_num(pool.pooled)}</div><div class="l">{scale_name}</div></div>
      <div class="kpi"><div class="v">{_num(pool.ci_low)}&ndash;{_num(pool.ci_high)}</div><div class="l">95% CI</div></div>
      <div class="kpi"><div class="v">{pool.k}</div><div class="l">Trials</div></div>
      <div class="kpi"><div class="v">{_num(pool.i2, 1)}%</div><div class="l">I&sup2;</div></div>
      <div class="kpi"><div class="v">{pi_cell}</div><div class="l">95% prediction interval</div></div>
    </div>
  </section>

  <section>
    <h2>Forest plot</h2>
    <div class="forest">{forest_svg}</div>
  </section>

  <section>
    <h2>Included trials</h2>
    <table>
      <thead><tr>
        <th>Trial</th><th>Registry</th><th class="num">Year</th>
        <th class="num">Data ({intervention} vs {comparator})</th>
        <th class="num">{scale} (95% CI)</th><th class="num">Weight</th>
      </tr></thead>
      <tbody>
      {trial_rows}
      </tbody>
    </table>
  </section>

  <section>
    <h2>Methods &amp; heterogeneity</h2>
    <table>
      <tr><td>Effect measure</td><td class="num">{scale_name} ({scale})</td></tr>
      <tr><td>Model</td><td class="num">Random effects (Paule&ndash;Mandel &tau;&sup2;)</td></tr>
      <tr><td>Confidence interval</td><td class="num">Knapp&ndash;Hartung (t<sub>k&minus;1</sub>){floor_note}</td></tr>
      <tr><td>Pooled estimate</td><td class="num">{_num(pool.pooled)} (95% CI {_num(pool.ci_low)} to {_num(pool.ci_high)})</td></tr>
      <tr><td>Prediction interval (Cochrane v6.5 t<sub>k&minus;1</sub>)</td><td class="num">{pi_cell}</td></tr>
      <tr><td>&tau;&sup2; (between-study variance)</td><td class="num">{_num(pool.tau2, 4)}</td></tr>
      <tr><td>I&sup2;</td><td class="num">{_num(pool.i2, 1)}%</td></tr>
      <tr><td>Cochran Q (df = {pool.Q_df})</td><td class="num">{_num(pool.Q, 2)}, p = {qp_fmt}</td></tr>
      <tr><td>Test of overall effect</td><td class="num">z = {_num(pool.z, 2)}, p = {_num(pool.p, 4)}</td></tr>
    </table>
  </section>

  <section>
    <div class="disclaimer">
      <strong>Auto-generated draft.</strong> This page summarises trial data
      supplied in the build configuration. Verify every extracted number
      against the source publication before citing. Effect estimates assume
      the supplied counts/effects are correct and the trials are clinically
      combinable. Not a substitute for a registered systematic-review protocol.
    </div>
  </section>

</main>
<footer>
  Generated offline by <code>meta-starter-kit</code> · random-effects Paule&ndash;Mandel + Knapp&ndash;Hartung +
  Cochrane v6.5 prediction interval · {authors or "no author set"}
</footer>
</body>
</html>
"""
