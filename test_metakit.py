"""Tests for the meta-starter-kit engine and build pipeline.

Run: python -m pytest test_metakit.py -v   (or just: python test_metakit.py)
"""
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from metakit import engine


def test_binary_effect_logor():
    """log-OR + variance from a clean 2x2 (no zero cells)."""
    e = engine.binary_effect("T", tE=50, tN=500, cE=70, cN=500)
    # OR = (50*430)/(450*70) = 21500/31500 = 0.6825
    assert abs(math.exp(e.yi) - 0.6825) < 1e-3
    # vi = 1/50 + 1/450 + 1/70 + 1/430
    assert abs(e.vi - (1/50 + 1/450 + 1/70 + 1/430)) < 1e-9


def test_binary_zero_cell_correction():
    """0.5 added to all cells only when a cell is zero."""
    e = engine.binary_effect("T", tE=0, tN=100, cE=5, cN=100)
    # With correction: (0.5*95.5)/(100.5*5.5)
    expected = math.log((0.5 * 95.5) / (100.5 * 5.5))
    assert abs(e.yi - expected) < 1e-9


def test_binary_no_correction_when_no_zero():
    e = engine.binary_effect("T", tE=10, tN=100, cE=20, cN=100)
    # No correction -> integer cells
    expected = math.log((10 * 80) / (90 * 20))
    assert abs(e.yi - expected) < 1e-9


def test_pm_tau2_converges_high_heterogeneity():
    """The case that broke the old estimator (tau2=887): small within-study
    variances, large between-study spread. PM must give a sane tau2 (~5)."""
    trials = [
        engine.precomputed_effect("A", -12.4, -13.4, -11.5, "MD"),
        engine.precomputed_effect("B", -10.3, -12.0, -8.6, "MD"),
        engine.precomputed_effect("C", -7.9, -9.0, -6.8, "MD"),
    ]
    pool = engine.pool_effects(trials, "MD")
    assert pool is not None
    assert 2.0 < pool.tau2 < 8.0, f"tau2 out of sane range: {pool.tau2}"
    assert 90 < pool.i2 < 99
    # Pool should be near the weighted middle, CI must be finite and sane
    assert -13 < pool.pooled < -7
    assert pool.ci_low > -30 and pool.ci_high < 5


def test_homogeneous_binary_pool_matches_reference():
    """Finerenone-style 3-trial OR pool. Reference (metafor on this exact
    data): OR ~ 0.848, I2 = 0, tau2 = 0."""
    trials = [
        engine.binary_effect("FIDELIO", 367, 2833, 420, 2841),
        engine.binary_effect("FIGARO", 458, 3686, 519, 3666),
        engine.binary_effect("FINEARTS", 624, 3003, 719, 2998),
    ]
    pool = engine.pool_effects(trials, "OR")
    assert abs(pool.pooled - 0.848) < 0.01
    assert pool.tau2 == 0.0
    assert pool.i2 < 1.0


def test_hksj_floor_applied_when_low_Q():
    """When Q < k-1, the HKSJ scale would be < 1; the floor must kick in."""
    # Three nearly-identical effects -> Q very small
    trials = [
        engine.precomputed_effect("A", 0.80, 0.70, 0.91, "OR"),
        engine.precomputed_effect("B", 0.81, 0.71, 0.92, "OR"),
        engine.precomputed_effect("C", 0.80, 0.70, 0.91, "OR"),
    ]
    pool = engine.pool_effects(trials, "OR")
    assert pool.hksj_floor_applied is True


def test_pi_undefined_for_k2():
    trials = [
        engine.binary_effect("A", 10, 100, 20, 100),
        engine.binary_effect("B", 12, 110, 19, 105),
    ]
    pool = engine.pool_effects(trials, "OR")
    assert pool.pi_low is None and pool.pi_high is None


def test_pi_defined_for_k3():
    trials = [
        engine.binary_effect("A", 10, 100, 20, 100),
        engine.binary_effect("B", 12, 110, 19, 105),
        engine.binary_effect("C", 8, 95, 17, 99),
    ]
    pool = engine.pool_effects(trials, "OR")
    assert pool.pi_low is not None and pool.pi_high is not None


def test_build_end_to_end(tmp_path):
    """build.py produces a valid HTML file with no None leaks."""
    cfg = {
        "title": "Test review",
        "intervention": "Drug",
        "comparator": "Placebo",
        "effect_measure": "OR",
        "trials": [
            {"name": "A", "tE": 10, "tN": 100, "cE": 20, "cN": 100},
            {"name": "B", "tE": 12, "tN": 110, "cE": 19, "cN": 105},
            {"name": "C", "tE": 8, "tN": 95, "cE": 17, "cN": 99},
        ],
    }
    cfg_path = tmp_path / "t.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "t.html"
    r = subprocess.run(
        [sys.executable, str(HERE / "build.py"), str(cfg_path), "--out", str(out)],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    # No Python-None leaks into the page
    assert ">None<" not in html
    assert "None%" not in html
    assert "<svg" in html  # forest plot present
    assert "Random-effects" in html or "random-effects" in html


def test_build_rejects_single_trial(tmp_path):
    cfg = {"title": "x", "effect_measure": "OR",
           "trials": [{"name": "A", "tE": 10, "tN": 100, "cE": 20, "cN": 100}]}
    cfg_path = tmp_path / "one.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(HERE / "build.py"), str(cfg_path)],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 2
    assert "at least 2 trials" in r.stderr


if __name__ == "__main__":
    # Minimal runner if pytest isn't installed.
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            import inspect
            if "tmp_path" in inspect.signature(fn).parameters:
                import tempfile
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
            print(f"  PASS {fn.__name__}")
            passed += 1
        except Exception:
            print(f"  FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
