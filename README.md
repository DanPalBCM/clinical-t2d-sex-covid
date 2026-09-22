# clinical-t2d-sex-covid

Analysis code for *"Sex Differences in the Clinical Course of Youth-Onset Type 2
Diabetes Before and After 2020"* (Palacios, Sobhi, et al.).

**Code only. No patient data, no patient-level output, no protected health
information.** See [Data availability](#data-availability).

## What this repository contains

| Path | Purpose |
|---|---|
| `analysis/foundry_analysis.py` | The analysis as authored, run inside Palantir Foundry against the governed dataset. Produces the aggregate result tables the manuscript reports. |
| `analysis/make_figures.py` | Builds every manuscript figure from the aggregate export. Runs anywhere; needs no Foundry access. |
| `analysis/figstyle.py` | Shared publication style (palette, soft-bar helpers, typography). |
| `analysis/dump_block.py` | Reads a named table out of the aggregate export dump. |
| `analysis/count_words.py` | Journal word-limit counter for the LaTeX source. |

## Analyses

- Baseline characteristics by sex, by calendar period, and by age at diagnosis
  (median [IQR] with Kruskal–Wallis; n (%) with chi-square).
- Three multivariable logistic regressions — diabetic ketoacidosis at diagnosis,
  hypertension at diagnosis, dyslipidemia at 2 years — each carrying a
  **sex × calendar-period interaction**, adjusted for age at diagnosis, race and
  ethnicity, and BMI *z*-score, plus sex-stratified simple effects.
- A linear mixed-effects model of HbA1c over time on the
  period × sex × time factorial, with a random intercept and a random slope on
  time per patient, fitted by REML.
- Sensitivity analyses: refits omitting BMI *z*-score on the full assessable
  denominators, and an alternative 15 March 2020 exposure cut-point.

## Reproducing the figures

The figure scripts read a tab-delimited dump of **aggregate** result tables
(group-level counts, percentages, model coefficients). That dump is not included
here — see below.

```bash
pip install pandas matplotlib
python analysis/make_figures.py      # -> figures/
```

## Data availability

The underlying clinical and administrative data are protected patient health
information governed by IRB protocols H-55929 and H-53771 and by institutional
data-use restrictions. They cannot be shared, deposited, or released on request.
De-identified aggregate data supporting the findings are provided in the article
and its supplementary materials.

The aggregate export dump is also withheld from this repository. Although it holds
no patient-level rows, some of its cells fall below a disclosure-safe count and
one provenance note records internal identifiers, so it is governed alongside the
source data rather than published.

## Cohort construction

The cohort, the type 2 diabetes case definition, the diagnostic exclusions, and
the outcome definitions are built by a shared upstream pipeline and are described
in the companion methodology paper on this dataset. The transforms for that
pipeline live in
[`clinical-diabetes-t1d-t2d`](https://github.com/DanPalBCM/clinical-diabetes-t1d-t2d).
This repository contains only the analysis specific to the present manuscript.

## Related repositories

- [`clinical-diabetes-t1d-t2d`](https://github.com/DanPalBCM/clinical-diabetes-t1d-t2d) — cohort construction and Foundry data transforms (parent methodology paper).
- [`clinical-t2d-biostats`](https://github.com/DanPalBCM/clinical-t2d-biostats) — risk-factor and prediction analyses on the same cohort.

## Citation

Manuscript under review. Please cite the published article once available.

## Acknowledgment

Figure design follows [PubliPlots](https://github.com/jorgebotas/publiplots)
(Botas, 2025).
