"""metakit — a complete, offline meta-analysis engine.

DO NOT EDIT this package to create a new meta-analysis. Everything here
is finished and tested. To make a new review, write a small config JSON
in configs/ and run `python build.py configs/your_review.json`.

Public surface:
    metakit.engine.pool_effects(...)   -> pooled estimate + heterogeneity
    metakit.forest.forest_svg(...)     -> inline SVG forest plot
    metakit.render.render_html(...)    -> full standalone HTML document
"""
from . import engine, forest, render  # noqa: F401

__version__ = "1.0.0"
