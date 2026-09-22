"""
Shared publication style + soft-bar helpers for the T2D Sex x COVID-era
manuscript figures.

Built on PubliPlots (Botas 2025, https://github.com/jorgebotas/publiplots) for a
consistent, publication-ready look:
  - publiplots' global rcParams (init_rcparams) for typography/spines/sizing,
  - thin, consistent bar widths,
  - soft fills + saturated outlines (+ optional hatch texture) instead of solid
    wide bars.

The palette stays this manuscript's own sex/era colour system so the sibling
papers never share a panel; only the *bar styling* and typography are borrowed
from PubliPlots.

Cite: Botas, J. (2025). PubliPlots: Publication-ready plotting for Python.
"""

import numpy as np
import matplotlib.pyplot as plt

try:
    import publiplots as pp
    _HAVE_PP = True
except Exception:                     # graceful fallback if not installed
    pp = None
    _HAVE_PP = False


# ── Bar geometry (keep bars thin & consistent across every figure) ───────────
BAR_W = 0.58          # single-series bar width fraction
GROUP_W = 0.72        # total width shared by a grouped-bar cluster

# rotating hatch textures for grouped / secondary bars (subtle, publication-safe)
HATCHES = ["", "///", "...", "\\\\\\", "xxx", "---"]

INK = "#2b2b2b"


def apply_style():
    """Apply the global publication style once, at import time of a generator."""
    if _HAVE_PP:
        pp.init_rcparams()
    plt.rcParams.update({
        "savefig.dpi": 300, "figure.dpi": 300,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "axes.spines.top": False, "axes.spines.right": False,
        "font.family": "sans-serif",
    })


def _lighten(hexc, amt=0.55):
    """Blend a hex colour toward white by `amt` (0=orig, 1=white)."""
    hexc = hexc.lstrip("#")
    r, g, b = (int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    r = int(r + (255 - r) * amt); g = int(g + (255 - g) * amt); b = int(b + (255 - b) * amt)
    return f"#{r:02x}{g:02x}{b:02x}"


def soft_fill(hexc, amt=0.55):
    """Public: the soft (lightened) fill colour for a base colour — handy for
    building matching legend proxy patches."""
    return _lighten(hexc, amt)


def soft_bars(ax, x, heights, base_colors, *, width=None, emphasis=None,
              horizontal=False, err=None, hatch=None, lighten=0.55, lw=1.3,
              ink=INK):
    """Draw bars with soft fills + saturated outlines (PubliPlots look).
      base_colors: per-bar saturated colour, or a single colour for all bars.
      emphasis   : index (or set) drawn SOLID to pop.
      hatch      : optional list of hatch strings per bar.
    Returns the bar container."""
    width = width if width is not None else BAR_W
    n = len(heights)
    if isinstance(base_colors, str):
        base_colors = [base_colors] * n
    emph = set() if emphasis is None else ({emphasis} if isinstance(emphasis, int) else set(emphasis))
    faces, edges = [], []
    for i, c in enumerate(base_colors):
        if i in emph:
            faces.append(c); edges.append("white")
        else:
            faces.append(_lighten(c, lighten)); edges.append(c)
    kw = dict(color=faces, edgecolor=edges, linewidth=lw)
    if hatch is not None:
        kw["hatch"] = hatch
    if horizontal:
        return ax.barh(x, heights, width, xerr=err, capsize=2.5,
                       error_kw={"lw": 0.9, "ecolor": ink}, **kw)
    return ax.bar(x, heights, width, yerr=err, capsize=2.5,
                  error_kw={"lw": 0.9, "ecolor": ink}, **kw)
