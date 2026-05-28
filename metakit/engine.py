"""Random-effects meta-analysis engine — pure Python, no dependencies.

Implements the methodology the rapidmeta project standardised on:
  * REML tau-squared (iterative, Viechtbauer 2005)
  * Knapp-Hartung (HKSJ) variance scaling with a FLOOR at 1 (Wiksten 2016)
    so that low-heterogeneity pools are not given falsely narrow CIs
  * Prediction interval via t_(k-1) per Cochrane Handbook v6.5 (undefined
    for k < 3)
  * Binary outcomes -> log odds ratio, Yates 0.5 correction ONLY when a
    cell is zero
  * Continuous / pre-computed effects -> pool the effect + its SE directly;
    ratio scales (HR/OR/RR) are pooled on the log scale and back-transformed

This file is finished. To create a new meta-analysis you do not edit it —
you write a config (see README.md) and run build.py.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional

RATIO_SCALES = {"OR", "HR", "RR"}
DIFF_SCALES = {"MD", "SMD", "RD"}


# ---------------------------------------------------------------------------
# Distribution helpers (no scipy)
# ---------------------------------------------------------------------------
def normal_cdf(z: float) -> float:
    """Standard normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def t_quantile_975(df: int) -> float:
    """Two-sided 97.5% Student-t quantile (upper-tail alpha = 0.025).

    Exact small-df table + Cornish-Fisher expansion for larger df. Good to
    ~1e-4 for df >= 2, which is well within display precision.
    """
    if df <= 0:
        return float("nan")
    table = {
        1: 12.7062, 2: 4.30265, 3: 3.18245, 4: 2.77645, 5: 2.57058,
        6: 2.44691, 7: 2.36462, 8: 2.306, 9: 2.26216, 10: 2.22814,
        11: 2.20099, 12: 2.1788, 13: 2.16037, 14: 2.14479, 15: 2.13145,
        16: 2.11991, 17: 2.10982, 18: 2.10092, 19: 2.09302, 20: 2.08596,
        21: 2.07961, 22: 2.07387, 23: 2.06866, 24: 2.0639, 25: 2.05954,
        26: 2.05553, 27: 2.05183, 28: 2.04841, 29: 2.04523, 30: 2.04227,
        40: 2.02108, 50: 2.00856, 60: 2.0003, 80: 1.99006, 100: 1.98397,
    }
    if df in table:
        return table[df]
    # Cornish-Fisher around the normal quantile for arbitrary df
    z = 1.959964
    g1 = (z**3 + z) / 4
    g2 = (5*z**5 + 16*z**3 + 3*z) / 96
    g3 = (3*z**7 + 19*z**5 + 17*z**3 - 15*z) / 384
    g4 = (79*z**9 + 776*z**7 + 1482*z**5 - 1920*z**3 - 945*z) / 92160
    return z + g1/df + g2/df**2 + g3/df**3 + g4/df**4


def _gammaincc(s: float, x: float) -> float:
    """Regularised upper incomplete gamma Q(s, x) — for the Q-test p-value."""
    if x <= 0 or s <= 0:
        return 1.0
    if x < s + 1:
        ap = s
        summ = 1.0 / s
        term = summ
        for _ in range(300):
            ap += 1
            term *= x / ap
            summ += term
            if abs(term) < abs(summ) * 1e-13:
                break
        return 1.0 - summ * math.exp(-x + s * math.log(x) - math.lgamma(s))
    b = x + 1 - s
    c = 1e300
    d = 1.0 / b
    h = d
    for i in range(1, 300):
        an = -i * (i - s)
        b += 2
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delt = d * c
        h *= delt
        if abs(delt - 1.0) < 1e-13:
            break
    return h * math.exp(-x + s * math.log(x) - math.lgamma(s))


def chi2_sf(x: float, df: int) -> float:
    """Upper-tail (survival) of the chi-square distribution."""
    if df <= 0:
        return float("nan")
    return _gammaincc(df / 2.0, x / 2.0)


# ---------------------------------------------------------------------------
# Effect-size construction
# ---------------------------------------------------------------------------
@dataclass
class TrialEffect:
    name: str
    yi: float            # effect on the analysis scale (log for ratios)
    vi: float            # variance of yi
    nct: Optional[str] = None
    year: Optional[int] = None
    pmid: Optional[str] = None
    # Raw inputs kept for display
    raw: dict = field(default_factory=dict)


def binary_effect(name, tE, tN, cE, cN, **meta) -> Optional[TrialEffect]:
    """Build a log-OR effect from a 2x2 table.

    tE/tN = events/total in the intervention arm,
    cE/cN = events/total in the comparator arm.
    Yates 0.5 added to ALL cells only if at least one cell is zero.
    Returns None if the trial is unusable.
    """
    tNE = tN - tE
    cNE = cN - cE
    cells = [tE, tNE, cE, cNE]
    if any(c < 0 for c in cells) or tN <= 0 or cN <= 0:
        return None
    if min(cells) == 0:
        a, b, c, d = tE + 0.5, tNE + 0.5, cE + 0.5, cNE + 0.5
    else:
        a, b, c, d = tE, tNE, cE, cNE
    try:
        yi = math.log((a * d) / (b * c))
        vi = 1/a + 1/b + 1/c + 1/d
    except (ValueError, ZeroDivisionError):
        return None
    if not (math.isfinite(yi) and math.isfinite(vi)) or vi <= 0:
        return None
    return TrialEffect(name=name, yi=yi, vi=vi,
                       raw={"tE": tE, "tN": tN, "cE": cE, "cN": cN}, **meta)


def precomputed_effect(name, effect, ci_low, ci_high, scale, **meta) -> Optional[TrialEffect]:
    """Build an effect from a published point estimate + 95% CI.

    For ratio scales the inputs are on the natural scale (e.g. HR 0.85,
    CI 0.72-0.99) and are log-transformed internally. For difference
    scales they are used directly.
    """
    z = 1.959964
    if scale in RATIO_SCALES:
        if effect <= 0 or ci_low <= 0 or ci_high <= 0:
            return None
        yi = math.log(effect)
        se = (math.log(ci_high) - math.log(ci_low)) / (2 * z)
    else:
        yi = effect
        se = (ci_high - ci_low) / (2 * z)
    if not (math.isfinite(yi) and math.isfinite(se)) or se <= 0:
        return None
    return TrialEffect(name=name, yi=yi, vi=se * se,
                       raw={"effect": effect, "ci_low": ci_low, "ci_high": ci_high},
                       **meta)


# ---------------------------------------------------------------------------
# Pooling
# ---------------------------------------------------------------------------
def _pm_tau2(yis, vis) -> float:
    """Paule-Mandel between-study variance via bisection.

    Solves  Sum_i w_i (y_i - mu_w)^2 = k - 1,  with w_i = 1/(v_i + tau^2)
    and mu_w the weighted mean. The left side is monotonically decreasing
    in tau^2, so bisection always converges — unlike the naive fixed-point
    iteration, which can diverge when within-study variances are small
    relative to between-study spread (the case that produced tau^2 = 887
    in an earlier build). Paule-Mandel is the Cochrane-recommended
    estimator for small k (advanced-stats.md: "Never use DL for k<10 —
    use REML or PM").
    """
    k = len(yis)
    if k < 2:
        return 0.0

    def gen_Q(tau2: float) -> float:
        ws = [1.0 / (v + tau2) for v in vis]
        sw = sum(ws)
        mu = sum(w * y for w, y in zip(ws, yis)) / sw
        return sum(w * (y - mu) ** 2 for w, y in zip(ws, yis))

    target = k - 1
    # If even at tau^2 = 0 the generalised Q is below k-1, there is no
    # excess heterogeneity -> tau^2 = 0.
    if gen_Q(0.0) <= target:
        return 0.0
    # Bracket the root: grow the upper bound until gen_Q drops below target.
    hi = 1.0
    for _ in range(200):
        if gen_Q(hi) < target:
            break
        hi *= 2.0
    else:
        return hi  # pathological; return the (large) bound rather than loop
    lo = 0.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        q = gen_Q(mid)
        if abs(q - target) < 1e-10:
            return mid
        if q > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@dataclass
class PoolResult:
    scale: str
    k: int
    # Display scale (back-transformed for ratios)
    pooled: float
    ci_low: float
    ci_high: float
    pi_low: Optional[float]
    pi_high: Optional[float]
    # Heterogeneity
    tau2: float
    i2: float
    h2: float
    Q: float
    Q_df: int
    Q_p: float
    # Inference
    z: float
    p: float
    se_log: float
    hksj_floor_applied: bool
    # Per-trial weights (percent) for the forest plot
    weights_pct: list
    trials: list


def pool_effects(trials: list, scale: str) -> Optional[PoolResult]:
    """REML + HKSJ(floored) random-effects pool of a list of TrialEffect."""
    k = len(trials)
    if k < 2:
        return None
    yis = [t.yi for t in trials]
    vis = [t.vi for t in trials]

    tau2 = _pm_tau2(yis, vis)
    ws = [1.0 / (v + tau2) for v in vis]
    sw = sum(ws)
    mu = sum(w * y for w, y in zip(ws, yis)) / sw
    var_mu = 1.0 / sw

    # Q at fixed-effect weights
    ws_fe = [1.0 / v for v in vis]
    mu_fe = sum(w * y for w, y in zip(ws_fe, yis)) / sum(ws_fe)
    Q = sum(w * (y - mu_fe) ** 2 for w, y in zip(ws_fe, yis))
    Q_df = k - 1
    Q_p = chi2_sf(Q, Q_df) if Q_df > 0 else float("nan")
    i2 = max(0.0, (Q - Q_df) / Q) * 100 if Q > 0 else 0.0
    h2 = max(1.0, Q / Q_df) if Q_df > 0 else 1.0

    # HKSJ scale with floor at 1
    scale_raw = sum(w * (y - mu) ** 2 for w, y in zip(ws, yis)) / (k - 1)
    hksj = max(1.0, scale_raw)
    se = math.sqrt(hksj * var_mu)
    floor_applied = scale_raw < 1.0

    t_crit = t_quantile_975(k - 1)
    ci_lo = mu - t_crit * se
    ci_hi = mu + t_crit * se

    if k >= 3:
        pi_se = math.sqrt(tau2 + se ** 2)
        pi_lo = mu - t_crit * pi_se
        pi_hi = mu + t_crit * pi_se
    else:
        pi_lo = pi_hi = None

    z = mu / se if se > 0 else float("nan")
    p = 2.0 * (1.0 - normal_cdf(abs(z))) if math.isfinite(z) else float("nan")

    weights_pct = [100.0 * w / sw for w in ws]

    if scale in RATIO_SCALES:
        disp = math.exp(mu)
        dlo, dhi = math.exp(ci_lo), math.exp(ci_hi)
        plo = math.exp(pi_lo) if pi_lo is not None else None
        phi = math.exp(pi_hi) if pi_hi is not None else None
    else:
        disp, dlo, dhi = mu, ci_lo, ci_hi
        plo, phi = pi_lo, pi_hi

    return PoolResult(
        scale=scale, k=k,
        pooled=disp, ci_low=dlo, ci_high=dhi,
        pi_low=plo, pi_high=phi,
        tau2=tau2, i2=i2, h2=h2, Q=Q, Q_df=Q_df, Q_p=Q_p,
        z=z, p=p, se_log=se, hksj_floor_applied=floor_applied,
        weights_pct=weights_pct, trials=trials,
    )


def per_trial_display(t: TrialEffect, scale: str):
    """Return (point, lo, hi) on the display scale for one trial."""
    z = 1.959964
    se = math.sqrt(t.vi)
    lo_log = t.yi - z * se
    hi_log = t.yi + z * se
    if scale in RATIO_SCALES:
        return math.exp(t.yi), math.exp(lo_log), math.exp(hi_log)
    return t.yi, lo_log, hi_log
