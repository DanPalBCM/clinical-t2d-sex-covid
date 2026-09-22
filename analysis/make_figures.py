#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the figures for the T2D sex x calendar-era manuscript from the Foundry
export dump. No Foundry needed.

SOURCE OF TRUTH, since 2026-09-17:
    foundry_exports/data_new_9172026/data_new.txt
The older foundry_exports/data.txt is superseded -- its numbers were produced by
an analysis layer that could not be reproduced in Foundry (wrong BMI scale, wrong
HbA1c variable, wrong event counts). Do not point this script back at it.

The new dump uses a tidy long schema, so the accessors below differ from the
pre-2026-09-17 version of this file:
    sex_by_period            + n_total, test, cutpoint   (TWO cut-points; filter!)
    sex_by_period_by_agecat  age_cat -> age_cat_label
    mm_marginal_means        period -> covid_pre_post, year -> year_window,
                             predicted_a1c -> predicted_mean_a1c, + ci_low/ci_high,
                             + n_patients, observed_mean

Figures, written to the directory matching where main.tex cites them:
  figures/main_figures/
    fig_sex_by_period.pdf      Fig 1. Proportion male pre- vs post-2020 (+ by age cat)
    fig_a1c_trajectory.pdf     Fig 2. HbA1c by sex and era: model fit (A) vs observed (B)
  figures/supplementary_figures/
    fig_or_forest.pdf          Fig S1. Adjusted ORs: sex, period, sex x period
    fig_participant_flow.pdf   Fig S2. STROBE participant flow

Usage:  python other/scripts/make_figures.py
"""
import os
import re
import io
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Shared PubliPlots-based publication style + soft-bar helpers (Botas 2025).
# Keeps this manuscript's own sex/era palette; borrows the thin soft-fill bar
# styling + typography from PubliPlots so the look matches the sibling papers.
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from figstyle import apply_style, soft_bars, soft_fill, BAR_W, HATCHES, INK

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(HERE)))  # unused; kept explicit below
PROJ = os.path.dirname(HERE)                      # other/
BASE = os.path.dirname(PROJ)                      # manuscript root
DATA = os.path.join(PROJ, "foundry_exports", "data_new_9172026", "data_new.txt")
# TWO output directories, matching where each figure is cited in main.tex.
# Figures 1 and 2 are main-text display items; the OR forest plot and the
# participant-flow diagram were demoted to supplementary items to meet the
# journal's four-display-item limit, so they belong in supplementary_figures/.
# main.tex's \graphicspath searches both, so a misfiled figure still COMPILES --
# which is exactly why it went unnoticed that both supplementary figures were
# being written to main_figures/ and supplementary_figures/ was empty. Keep each
# savefig pointed at the directory matching its role.
OUT = os.path.join(BASE, "figures", "main_figures")
OUT_SUPP = os.path.join(BASE, "figures", "supplementary_figures")
os.makedirs(OUT, exist_ok=True)
os.makedirs(OUT_SUPP, exist_ok=True)

CUTPOINT = "2020-01-01"          # primary exposure boundary; 2020-03-15 is the sensitivity


# ── Parse the multi-table dump into {name: DataFrame} ────────────────────────
def load_blocks(path):
    with open(path) as f:
        lines = f.read().split("\n")
    blocks, name, buf = {}, None, []
    name_re = re.compile(r"^[a-z][a-z0-9_]+$")

    def flush(nm, rows):
        rows = [r for r in rows if r.strip() != ""]
        if not nm or not rows:
            return
        blocks[nm] = pd.read_csv(io.StringIO("\n".join(rows)), sep="\t")

    for ln in lines:
        if name_re.match(ln.strip()) and ln == ln.strip():
            flush(name, buf)
            name, buf = ln.strip(), []
        else:
            buf.append(ln)
    flush(name, buf)
    return blocks


B = load_blocks(DATA)


def pfmt(p):
    """Style guide S5: exact p to three decimals down to 0.001, then p < 0.001."""
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def to_mmol(pct):
    """NGSP -> IFCC. mmol/mol = (% - 2.15) x 10.929."""
    return (pct - 2.15) * 10.929


# ── Style ────────────────────────────────────────────────────────────────────
apply_style()
C_MALE = "#2166ac"
C_FEMALE = "#b2182b"
C_PRE = "#7b3294"
C_POST = "#008837"


# ════════════════════════════════════════════════════════════════════════════
# FIGURE 1 — proportion male by calendar era (overall + by age category)
# ════════════════════════════════════════════════════════════════════════════
def fig_sex_by_period():
    sp = B["sex_by_period"].copy()
    sp = sp[sp["cutpoint"] == CUTPOINT]           # drop the 2020-03-15 sensitivity rows
    spa = B["sex_by_period_by_agecat"].copy()

    order = ["Pre_Covid", "Post_Covid"]
    lab = {"Pre_Covid": "Pre-2020", "Post_Covid": "Post-2020"}
    sp = sp.set_index("period").loc[order]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4.2))

    # Panel A — overall
    x = list(range(len(order)))
    vals = sp["pct_male"].values
    ns = sp["n_total"].values
    soft_bars(ax1, x, vals, [C_PRE, C_POST], width=BAR_W)
    for xi, v, n in zip(x, vals, ns):
        ax1.text(xi, v + 0.8, f"{v:.1f}%", ha="center", va="bottom",
                 fontsize=11, fontweight="bold")
    ax1.axhline(50, color="#888", lw=0.8, ls=":")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([f"{lab[o]}\n(n = {n:,})" for o, n in zip(order, ns)], fontsize=10.5)
    ax1.set_ylabel("Male (% of patients diagnosed)", fontsize=11)
    ax1.set_ylim(0, 60)
    ax1.set_title(f"A  Overall  ({pfmt(sp['p_value'].iloc[0])})",
                  loc="left", fontweight="bold", fontsize=12)

    # Panel B — by age category
    ages = ["Under 12", "12 and over"]
    width = 0.38
    xb = range(len(ages))
    pre = [spa[(spa.age_cat_label == a) & (spa.period == "Pre_Covid")]["pct_male"].iloc[0] for a in ages]
    post = [spa[(spa.age_cat_label == a) & (spa.period == "Post_Covid")]["pct_male"].iloc[0] for a in ages]
    pvals = [spa[spa.age_cat_label == a]["p_value"].iloc[0] for a in ages]
    xpre = [i - width / 2 for i in xb]
    xpost = [i + width / 2 for i in xb]
    b1 = soft_bars(ax2, xpre, pre, C_PRE, width=width, hatch=[HATCHES[0]] * len(pre))
    b2 = soft_bars(ax2, xpost, post, C_POST, width=width, hatch=[HATCHES[1]] * len(post))
    for bars in (b1, b2):
        for rect in bars:
            ax2.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 0.8,
                     f"{rect.get_height():.1f}", ha="center", va="bottom", fontsize=9)
    ax2.axhline(50, color="#888", lw=0.8, ls=":")
    ax2.set_xticks(list(xb))
    ax2.set_xticklabels([f"{a}\n({pfmt(pv)})" for a, pv in zip(ages, pvals)], fontsize=10)
    ax2.set_ylim(0, 60)
    ax2.set_ylabel("Male (%)", fontsize=11)
    ax2.set_title("B  By age at diagnosis", loc="left", fontweight="bold", fontsize=12)
    ax2.legend(handles=[Patch(facecolor=soft_fill(C_PRE), edgecolor=C_PRE,
                              hatch=HATCHES[0], label="Pre-2020"),
                        Patch(facecolor=soft_fill(C_POST), edgecolor=C_POST,
                              hatch=HATCHES[1], label="Post-2020")],
               frameon=False, fontsize=10, loc="upper left")

    fig.suptitle("Male representation in youth-onset type 2 diabetes before vs. after 2020",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    for ext in ("pdf", "svg"):
        fig.savefig(os.path.join(OUT, f"fig_sex_by_period.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_sex_by_period")


# ════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — HbA1c by sex and era: model fit (A) against observed means (B)
#
# Two panels on purpose. The mixed model is linear in the follow-up window, and
# the observed course is not: HbA1c falls by 2 years and rises again by 5. The
# linear term therefore extrapolates the post-2020 5-year cells (n = 41 and 25)
# far below what was measured -- 6.4% predicted against 8.0% observed in females,
# 5.7% against 9.1% in males. Plotting the fit alone would hide that; plotting
# the fit and the data side by side is the honest presentation, and the 2-to-5
# year segments are dashed to mark where the fit is not supported.
# ════════════════════════════════════════════════════════════════════════════
def fig_a1c_trajectory():
    mm = B["mm_marginal_means"].copy()
    style = {
        # (colour, marker, label, y-offset in points for the 5-year cell label;
        #  pre-2020 labels sit above the marker, post-2020 below, so the pre-2020
        #  female and post-2020 male cells at year 5 do not overprint)
        ("Pre_Covid", "Male"):    (C_MALE, "o", "Male · Pre-2020", 8),
        ("Pre_Covid", "Female"):  (C_FEMALE, "o", "Female · Pre-2020", 8),
        ("Post_Covid", "Male"):   (C_MALE, "s", "Male · Post-2020", -9),
        ("Post_Covid", "Female"): (C_FEMALE, "s", "Female · Post-2020", -9),
    }
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.4, 5.0), sharey=True)

    for (period, sex), (col, mk, lbl, dy) in style.items():
        g = mm[(mm.covid_pre_post == period) & (mm.sex == sex)].sort_values("year_window")
        yrs = g["year_window"].values
        pred = g["predicted_mean_a1c"].values
        obs = g["observed_mean"].values
        lo, hi = g["ci_low"].values, g["ci_high"].values
        dense = yrs <= 2                      # 0-2 years: where the data are dense

        # Panel A — model
        axA.fill_between(yrs, lo, hi, color=col, alpha=0.10, lw=0, zorder=1)
        axA.plot(yrs[dense], pred[dense], color=col, ls="-", lw=2, zorder=3)
        axA.plot(yrs[~dense | (yrs == 2)], pred[~dense | (yrs == 2)],
                 color=col, ls=":", lw=2, zorder=3)
        axA.plot(yrs, pred, mk, color=col, markersize=8, markeredgecolor="white",
                 markeredgewidth=1.1, label=lbl, zorder=4)
        # Panel B — observed
        axB.plot(yrs, obs, color=col, ls="-", lw=1.6, alpha=0.85, zorder=3)
        axB.plot(yrs, obs, mk, color=col, markersize=8, markeredgecolor="white",
                 markeredgewidth=1.1, zorder=4, label=lbl)
        # Label only the 5-year cells: they are the sparse ones, and they are where
        # the fit in panel A departs from the data. Labelling every cell collided.
        for y, v, n in zip(yrs, obs, g["n_patients"].values):
            if y == 5:
                axB.annotate(f"n = {n}", (y, v), textcoords="offset points",
                             xytext=(-9, dy), ha="right", va="center",
                             fontsize=8, color=col)

    years = sorted(mm["year_window"].unique())
    for ax in (axA, axB):
        ax.set_xticks(years)
        ax.set_xticklabels([("Diagnosis" if y == 0 else f"Year {y:g}") for y in years],
                           fontsize=10.5)
        ax.set_xlabel("Follow-up window", fontsize=11.5)
        ax.yaxis.set_major_locator(ticker.MultipleLocator(0.5))
        ax.grid(axis="y", ls=":", lw=0.7, color="#cccccc", zorder=0)
    axA.set_ylabel("Mean HbA1c (%)", fontsize=11.5)
    axA.set_title("A  Mixed-model predicted mean (95% CI)", loc="left",
                  fontweight="bold", fontsize=12)
    axB.set_title("B  Observed mean", loc="left", fontweight="bold", fontsize=12)
    axA.legend(frameon=False, fontsize=9, loc="lower left", ncol=1)
    # What the dotted segments mean is stated in the figure legend, not on the panel;
    # an in-panel note collided with the key at every position tried.
    axB.annotate("cell sizes for every window are in the figure legend",
                 xy=(0.97, 0.04), xycoords="axes fraction", ha="right",
                 fontsize=8, color="#555")

    # Secondary axis in mmol/mol (IFCC), required for a Diabetes Care submission.
    ax2 = axB.twinx()
    ax2.spines["right"].set_visible(True)
    lo, hi = axA.get_ylim()
    ax2.set_ylim(to_mmol(lo), to_mmol(hi))
    ax2.set_ylabel("Mean HbA1c (mmol/mol)", fontsize=11.5)
    ax2.yaxis.set_major_locator(ticker.MultipleLocator(10))

    # "calendar era", NOT "COVID era": the manuscript frames the exposure as
    # calendar period throughout, because a genuine pandemic effect is only one of
    # three candidate explanations it can distinguish (the others being changed
    # ascertainment and the age-composition shift). The caption says "calendar
    # era", so the panel title must too.
    fig.suptitle("HbA1c by sex and calendar era: model fit against observed means",
                 fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout()
    for ext in ("pdf", "svg"):
        fig.savefig(os.path.join(OUT, f"fig_a1c_trajectory.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_a1c_trajectory")


# ════════════════════════════════════════════════════════════════════════════
# FIGURE S1 — adjusted OR forest: sex, period, and the sex x period interaction
#
# The interaction terms are the paper's pre-specified test, so they belong on the
# plot next to the main effects rather than only in the table. Series are keyed by
# marker shape as well as colour, so the figure survives greyscale printing.
# ════════════════════════════════════════════════════════════════════════════
def fig_or_forest():
    specs = [
        ("logit_dka", "DKA at diagnosis"),
        ("logit_htn_dx", "Hypertension at diagnosis"),
        ("logit_dyslip_2yr", "Dyslipidemia at 2 years"),
    ]
    # Patsy term names, as the new export writes them.
    terms = [
        ("C(sex)[T.Male]", "Male vs. female", C_MALE, "o"),
        ("C(covid_pre_post)[T.Post_Covid]", "Post- vs. pre-2020", C_POST, "s"),
        ("C(sex)[T.Male]:C(covid_pre_post)[T.Post_Covid]",
         "Sex × period interaction", "#555555", "D"),
    ]
    rows = []
    for name, pretty in specs:
        d = B[name]
        d = d[d.model == name]          # primary model only, not the stratified refits
        for term, tlab, col, mk in terms:
            r = d[d.term == term].iloc[0]
            rows.append((pretty, tlab, col, mk,
                         r.estimate_or, r.ci_low, r.ci_high, r.p_value))

    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    ys = list(range(len(rows)))[::-1]
    for y, (pretty, tlab, col, mk, orr, lo, hi, p) in zip(ys, rows):
        ax.plot([lo, hi], [y, y], color=col, lw=2, zorder=2)
        ax.plot(orr, y, mk, color=col, markersize=8, markeredgecolor="white",
                markeredgewidth=1.1, zorder=3)
        ax.text(3.9, y, f"{orr:.2f} ({lo:.2f}–{hi:.2f}), {pfmt(p)}",
                va="center", fontsize=8.5)
    ax.axvline(1.0, color="#444", lw=1.0, ls="--", zorder=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{pretty}\n{tlab}" for (pretty, tlab, *_) in rows], fontsize=8.5)
    ax.set_xlabel("Adjusted odds ratio (95% CI)", fontsize=12)
    ax.set_xlim(0.3, 3.9)
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%.1f"))
    ax.set_xticks([0.5, 1, 2, 3])
    ax.legend(handles=[Line2D([], [], color=c, marker=m, ls="-", lw=2,
                              markersize=7, markeredgecolor="white", label=t)
                       for _, t, c, m in terms],
              frameon=False, fontsize=9, loc="lower left", bbox_to_anchor=(0.0, -0.20),
              ncol=3)
    ax.set_title("Adjusted associations with sex, calendar period, and their interaction",
                 fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    for ext in ("pdf", "svg"):
        fig.savefig(os.path.join(OUT_SUPP, f"fig_or_forest.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_or_forest")


# ════════════════════════════════════════════════════════════════════════════
# FIGURE S2 — participant flow (STROBE)
#
# The ENDPOINT counts are READ FROM the participant_flow block, never typed in, so
# they cannot drift from the export the way the Methods prose once did (it named
# three losses between 2,491 and 2,489, which sums to 2,488).
#
# *** THE LOSS MECHANISM IS THE SIBLINGS', NOT THIS EXPORT'S (2026-09-22). ***
# participant_flow's step LABELS attribute the 2,491 -> 2,489 loss to one manual
# chart-review exclusion plus one patient lost inside 11_outcomes.py. The sibling
# T2D_Biostats and the parent CEDAR manuscript both say the two patients fell
# outside the 8-20-year age range, and on Daniel's instruction THE SIBLINGS ARE
# AUTHORITATIVE on the shared cohort -- this manuscript was the wrong one. So the
# diagram shows ONE two-patient age-eligibility step, not two one-patient steps.
# Only the labels change; 2,491 and 2,489 are still read from the block, so the
# arithmetic is still export-checked.
#
# SCOPE IS DELIBERATE. The upstream cohort build belongs to the parent CEDAR /
# Pediatric Diabetes manuscript, so the top box states the case definition is
# applied there and does NOT redraw its exclusion funnel. This figure covers only
# what is this paper's own: the age-eligibility step to the analytic N, then the
# four analysis sets. Three papers must not print the same diagram.
#
# DISCLOSURE: every cell here is >= 778, far above any threshold, and the
# two-patient loss is a step *difference*, not a cell describing patients.
# ════════════════════════════════════════════════════════════════════════════
def fig_participant_flow():
    pf = B["participant_flow"].set_index("step")["n"].to_dict()

    def n(key):
        for k, v in pf.items():
            if k.strip().lower().startswith(key.lower()):
                return int(v)
        raise KeyError(key)

    rows_src = n("Rows in the source")
    n_def = n("Distinct patients meeting")
    n_analytic = n("Analytic cohort")
    n_bmi = n("... with complete BMI")
    n_a1c = n("... with >=1 HbA1c")
    n_htn = n("... hypertension at diagnosis assessable")
    n_dys = n("... dyslipidemia at 2 years assessable")

    main_boxes = [
        (f"Source extract\n{rows_src:,} laboratory rows",
         "one row per HbA1c observation"),
        (f"Patients meeting the type 2 diabetes\ncase definition  (n = {n_def:,})",
         "case definition applied upstream;\nsee companion methodology paper"),
        (f"Analytic cohort\n(N = {n_analytic:,})",
         f"−{n_def - n_analytic} outside the 8–20-year\nage range at diagnosis"),
    ]
    sets = [
        (f"Complete\nBMI $z$-score\n{n_bmi:,}", "3 logistic models"),
        (f"≥ 1 HbA1c\nvalue\n{n_a1c:,}", "mixed-effects model"),
        (f"Hypertension\nassessable\n{n_htn:,}", f"of {n_analytic:,}"),
        (f"Dyslipidemia\nassessable\n{n_dys:,}", f"of {n_analytic:,}"),
    ]

    fig, ax = plt.subplots(figsize=(9.2, 8.6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 10.6); ax.axis("off")

    BW, BH, CX = 5.6, 1.02, 6.0
    # Derived from len(main_boxes) so the chain cannot fall out of step with the
    # boxes again if a step is ever added or removed.
    tops = [9.5 - 1.75 * i for i in range(len(main_boxes))]
    for (label, side), ytop in zip(main_boxes, tops):
        emph = label.startswith("Analytic cohort")
        ax.add_patch(plt.Rectangle(
            (CX - BW / 2, ytop - BH), BW, BH,
            facecolor=soft_fill(C_POST, 0.80 if emph else 0.93),
            edgecolor=C_POST if emph else INK,
            linewidth=1.6 if emph else 1.1, zorder=2))
        ax.text(CX, ytop - BH / 2, label, ha="center", va="center",
                fontsize=10.2, fontweight="bold" if emph else "normal", zorder=3)
        ax.annotate(side, xy=(CX + BW / 2 + 0.18, ytop - BH / 2),
                    ha="left", va="center", fontsize=8.6, color="#555555",
                    zorder=3)

    for ytop, nxt in zip(tops[:-1], tops[1:]):
        ax.annotate("", xy=(CX, nxt), xytext=(CX, ytop - BH),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2))

    # Vertical connector STOPS above the "Analysis sets" label; the fan-out to the
    # four boxes then starts BELOW it, from y_fan. Previously both the connector and
    # the four elbow arrows originated at the label's own y, so the line was drawn
    # straight through the text.
    y_an = tops[-1] - BH
    y_lab = y_an - 0.40
    y_fan = y_an - 0.74
    ax.annotate("", xy=(CX, y_lab + 0.14), xytext=(CX, y_an),
                arrowprops=dict(arrowstyle="-", color=INK, lw=1.2))
    ax.text(CX, y_lab, "Analysis sets (not mutually exclusive)",
            ha="center", va="center", fontsize=9.4, style="italic",
            color="#444444", zorder=4)
    ax.annotate("", xy=(CX, y_fan), xytext=(CX, y_lab - 0.14),
                arrowprops=dict(arrowstyle="-", color=INK, lw=1.2))

    sw, gap, sh = 2.60, 0.26, 1.46
    x0 = CX - (4 * sw + 3 * gap) / 2
    sy = y_fan - 0.46
    # Horizontal spine joining the fan-out to each box, then a short drop per box.
    ax.annotate("", xy=(x0 + sw / 2, y_fan), xytext=(x0 + 3 * (sw + gap) + sw / 2, y_fan),
                arrowprops=dict(arrowstyle="-", color=INK, lw=1.0))
    for i, (label, sub) in enumerate(sets):
        xl = x0 + i * (sw + gap)
        ax.add_patch(plt.Rectangle((xl, sy - sh), sw, sh,
                                   facecolor=soft_fill(C_MALE, 0.90),
                                   edgecolor=INK, linewidth=1.0, zorder=2))
        ax.text(xl + sw / 2, sy - 0.52, label, ha="center", va="center",
                fontsize=9.3, linespacing=1.35, zorder=3)
        ax.text(xl + sw / 2, sy - 1.24, sub, ha="center", va="center",
                fontsize=8.2, color="#555555", zorder=3)
        ax.annotate("", xy=(xl + sw / 2, sy), xytext=(xl + sw / 2, y_fan),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9))

    fig.tight_layout()
    for ext in ("pdf", "svg"):
        fig.savefig(os.path.join(OUT_SUPP, f"fig_participant_flow.{ext}"),
                    bbox_inches="tight")
    plt.close(fig)
    print("  wrote fig_participant_flow")


if __name__ == "__main__":
    print(f"reading {DATA}")
    fig_sex_by_period()
    fig_a1c_trajectory()
    fig_or_forest()
    fig_participant_flow()
    print(f"main figures      -> {OUT}")
    print(f"supplementary     -> {OUT_SUPP}")
