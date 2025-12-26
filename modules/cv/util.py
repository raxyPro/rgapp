from __future__ import annotations

from flask import render_template


def generate_onepage_html(v):
    """Generate a one-page CV HTML from a vCard-like object (RBCVPair)."""
    return render_template(
        "cv/onepage_generated.html",
        v=v,
    )
