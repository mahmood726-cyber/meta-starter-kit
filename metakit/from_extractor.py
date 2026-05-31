"""
OPTIONAL bridge: auto-populate a meta-starter-kit config from trial texts using
the rct-extractor-v2 cardiology/malaria extractor.

The kit itself stays offline + zero-dependency: this module is only imported when
you choose to. It pulls poolable data (precomputed effects for cardiology;
raw 2x2 counts for malaria binary outcomes) out of each trial's abstract/results
text and returns a config that build.py consumes directly.

Setup: have rct-extractor-v2 importable, or point RCT_EXTRACTOR_PATH at its repo
root:
    set RCT_EXTRACTOR_PATH=C:\\Projects\\rct-extractor-v2

Usage:
    from metakit.from_extractor import config_from_records
    cfg = config_from_records(records, title="AL vs SP ACPR",
                              effect_measure="RR", endpoint="ACPR")
    # then: build a page from cfg via build.py / metakit.engine
"""
import os
import sys


def _load_extractor():
    p = os.getenv("RCT_EXTRACTOR_PATH")
    if p and p not in sys.path:
        sys.path.insert(0, p)
    try:
        from src.core.enhanced_extractor_v3 import EnhancedExtractor
        from src.bridges.meta_starter_kit import build_config_from_records
        return EnhancedExtractor, build_config_from_records
    except Exception as exc:   # pragma: no cover - depends on external repo
        raise RuntimeError(
            "rct-extractor-v2 is not importable. Install it or set "
            "RCT_EXTRACTOR_PATH to its repo root.") from exc


def config_from_records(records, *, title, effect_measure, endpoint=None, **meta):
    """records: [{name, text, nct?, pmid?, year?}] -> meta-starter-kit config dict.

    Topic-routed by the extractor: cardiology/general text yields precomputed
    effect estimates; malaria binary outcomes yield raw 2x2 counts.
    """
    EnhancedExtractor, build_config_from_records = _load_extractor()
    return build_config_from_records(
        records, EnhancedExtractor(), title=title,
        effect_measure=effect_measure, endpoint=endpoint, **meta)
