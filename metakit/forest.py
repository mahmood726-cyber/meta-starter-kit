"""Inline SVG forest plot — no JS, no external libraries.

Renders a classic meta-analysis forest plot: one row per trial (point +
95% CI whisker, box area proportional to weight), then a diamond for the
random-effects pooled estimate, a vertical line at the null, and a
prediction-interval bar. Works offline and prints cleanly.

Finished. Not edited per-review.
"""
from __future__ import annotations
import math
from .engine import RATIO_SCALES, per_trial_display


def _fmt(v, ratio):
    if v is None:
        return "—"
    return f"{v:.2f}"


def forest_svg(pool, scale: str, *, intervention="Intervention",
               comparator="Comparator") -> str:
    trials = pool.trials
    k = len(trials)
    ratio = scale in RATIO_SCALES
    null_val = 1.0 if ratio else 0.0

    # ---- layout constants -------------------------------------------------
    row_h = 26
    top = 70
    bottom_pad = 90
    width = 760
    plot_x0 = 300        # left edge of the plotting area
    plot_x1 = 560        # right edge
    label_x = 16
    height = top + (k + 2) * row_h + bottom_pad

    # ---- determine x-scale (log for ratios) ------------------------------
    pts = []
    for t in trials:
        p, lo, hi = per_trial_display(t, scale)
        pts.extend([lo, hi])
    pts.extend([pool.ci_low, pool.ci_high])
    if pool.pi_low is not None:
        pts.extend([pool.pi_low, pool.pi_high])
    pts = [v for v in pts if v is not None and v > (0 if ratio else -1e9) and math.isfinite(v)]

    if ratio:
        lo_b = max(min(pts) * 0.8, 1e-3)
        hi_b = max(pts) * 1.2
        tlo, thi = math.log(lo_b), math.log(hi_b)

        def xpos(v):
            v = max(v, 1e-6)
            return plot_x0 + (math.log(v) - tlo) / (thi - tlo) * (plot_x1 - plot_x0)
    else:
        span = max(pts) - min(pts)
        lo_b = min(pts) - span * 0.1
        hi_b = max(pts) + span * 0.1

        def xpos(v):
            return plot_x0 + (v - lo_b) / (hi_b - lo_b) * (plot_x1 - plot_x0)

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    svg = []
    svg.append(
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="system-ui,-apple-system,sans-serif" font-size="12" '
        f'role="img" aria-label="Forest plot of {esc(scale)} for {k} trials">'
    )
    svg.append(f'<rect width="{width}" height="{height}" fill="#ffffff"/>')

    # Column headers
    svg.append(f'<text x="{label_x}" y="34" font-weight="600">Trial</text>')
    svg.append(f'<text x="200" y="34" font-weight="600" text-anchor="end">Weight</text>')
    svg.append(f'<text x="{(plot_x0+plot_x1)/2:.0f}" y="34" font-weight="600" text-anchor="middle">{esc(scale)} (95% CI)</text>')
    svg.append(f'<text x="{plot_x1+12}" y="34" font-weight="600">Estimate</text>')
    svg.append(f'<line x1="{label_x}" y1="44" x2="{width-16}" y2="44" stroke="#cbd5e1"/>')

    # Null reference line
    xn = xpos(null_val)
    plot_top = top - 8
    plot_bot = top + (k + 1) * row_h
    svg.append(f'<line x1="{xn:.1f}" y1="{plot_top}" x2="{xn:.1f}" y2="{plot_bot}" '
               f'stroke="#94a3b8" stroke-dasharray="4 3"/>')

    # Per-trial rows
    max_w = max(pool.weights_pct) if pool.weights_pct else 1
    for i, t in enumerate(trials):
        y = top + i * row_h + row_h / 2
        p, lo, hi = per_trial_display(t, scale)
        name = esc(t.name)[:34]
        wpct = pool.weights_pct[i]
        # label + weight
        svg.append(f'<text x="{label_x}" y="{y+4:.0f}">{name}</text>')
        svg.append(f'<text x="200" y="{y+4:.0f}" text-anchor="end" fill="#475569">{wpct:.1f}%</text>')
        # whisker
        x_lo, x_hi, x_p = xpos(lo), xpos(hi), xpos(p)
        x_lo = max(plot_x0 - 4, min(plot_x1 + 4, x_lo))
        x_hi = max(plot_x0 - 4, min(plot_x1 + 4, x_hi))
        svg.append(f'<line x1="{x_lo:.1f}" y1="{y:.1f}" x2="{x_hi:.1f}" y2="{y:.1f}" stroke="#334155"/>')
        # box (area ~ weight)
        bs = 4 + 8 * math.sqrt(wpct / max_w) if max_w > 0 else 6
        svg.append(f'<rect x="{x_p-bs/2:.1f}" y="{y-bs/2:.1f}" width="{bs:.1f}" height="{bs:.1f}" fill="#2563eb"/>')
        # estimate text
        est = f'{_fmt(p, ratio)} ({_fmt(lo, ratio)}, {_fmt(hi, ratio)})'
        svg.append(f'<text x="{plot_x1+12}" y="{y+4:.0f}" fill="#1e293b">{est}</text>')

    # Pooled diamond
    yd = top + k * row_h + row_h / 2 + 4
    xl, xr, xc = xpos(pool.ci_low), xpos(pool.ci_high), xpos(pool.pooled)
    xl = max(plot_x0 - 4, xl); xr = min(plot_x1 + 4, xr)
    dh = 7
    svg.append(
        f'<polygon points="{xl:.1f},{yd:.1f} {xc:.1f},{yd-dh:.1f} {xr:.1f},{yd:.1f} {xc:.1f},{yd+dh:.1f}" '
        f'fill="#dc2626"/>'
    )
    svg.append(f'<text x="{label_x}" y="{yd+4:.0f}" font-weight="600">Random-effects pool</text>')
    pooled_est = f'{_fmt(pool.pooled, ratio)} ({_fmt(pool.ci_low, ratio)}, {_fmt(pool.ci_high, ratio)})'
    svg.append(f'<text x="{plot_x1+12}" y="{yd+4:.0f}" font-weight="600" fill="#b91c1c">{pooled_est}</text>')

    # Prediction-interval bar (below the diamond)
    if pool.pi_low is not None:
        yp = yd + row_h
        xpl, xph = xpos(pool.pi_low), xpos(pool.pi_high)
        xpl = max(plot_x0 - 4, xpl); xph = min(plot_x1 + 4, xph)
        svg.append(f'<line x1="{xpl:.1f}" y1="{yp:.1f}" x2="{xph:.1f}" y2="{yp:.1f}" '
                   f'stroke="#dc2626" stroke-width="2" stroke-dasharray="2 2"/>')
        svg.append(f'<text x="{label_x}" y="{yp+4:.0f}" fill="#b91c1c">95% prediction interval</text>')
        pi_est = f'{_fmt(pool.pi_low, ratio)} to {_fmt(pool.pi_high, ratio)}'
        svg.append(f'<text x="{plot_x1+12}" y="{yp+4:.0f}" fill="#b91c1c">{pi_est}</text>')

    # Axis + favours labels
    axis_y = plot_bot + 16
    svg.append(f'<line x1="{plot_x0}" y1="{axis_y}" x2="{plot_x1}" y2="{axis_y}" stroke="#334155"/>')
    # ticks
    if ratio:
        for tick in (0.1, 0.2, 0.5, 1, 2, 5, 10):
            if lo_b <= tick <= hi_b:
                xt = xpos(tick)
                svg.append(f'<line x1="{xt:.1f}" y1="{axis_y}" x2="{xt:.1f}" y2="{axis_y+4}" stroke="#334155"/>')
                svg.append(f'<text x="{xt:.1f}" y="{axis_y+16}" text-anchor="middle" fill="#475569">{tick:g}</text>')
    else:
        import math as _m
        lo_t = _m.floor(lo_b)
        hi_t = _m.ceil(hi_b)
        step = max(1, round((hi_t - lo_t) / 6))
        tick = lo_t
        while tick <= hi_t:
            if lo_b <= tick <= hi_b:
                xt = xpos(tick)
                svg.append(f'<line x1="{xt:.1f}" y1="{axis_y}" x2="{xt:.1f}" y2="{axis_y+4}" stroke="#334155"/>')
                svg.append(f'<text x="{xt:.1f}" y="{axis_y+16}" text-anchor="middle" fill="#475569">{tick:g}</text>')
            tick += step

    fav_y = axis_y + 36
    svg.append(f'<text x="{xn-8:.1f}" y="{fav_y}" text-anchor="end" fill="#16a34a">&#9664; favours {esc(intervention)}</text>')
    svg.append(f'<text x="{xn+8:.1f}" y="{fav_y}" fill="#b91c1c">favours {esc(comparator)} &#9654;</text>')

    svg.append("</svg>")
    return "\n".join(svg)
