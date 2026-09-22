# -*- coding: utf-8 -*-
"""
@author: sukru

ORIGINAL abstract-stage analysis code, preserved verbatim as the source of truth
for the Sex x COVID-era T2D study ("Paper 3").

Runs INSIDE Palantir Foundry against Dataset.get("t2d_outcomes").
Requires: pip install tableone openpyxl statsmodels pandas numpy matplotlib

Re-run instructions and the list of exports to produce live in:
    ../additional_analysis/REPRODUCE_SEX_COVID_ANALYSES.md

NOTE before re-running on the corrected dataset:
  * Run against the POST-DBP-fix corrected matrix.
  * Set pval=True in every TableOne call (shipped default is False; the abstract
    quotes p-values).
  * Do NOT ship the hard-coded observed means in the "BEST PLOT" cell —
    regenerate the trajectory from the mixed-model marginal means.
"""

#### **************************************************************************
###   t2d_dataset COVID STUDY Preprocessing for T2D Cohort
#### **************************************************************************

import pandas as pd
import numpy as np
from foundry.transforms import Dataset

# ============================================================================
# PREPROCESSING FUNCTIONS
# ============================================================================

_BMI_COLS = ["bmi_at_diagnosis", "bmi_at_2_years", "bmi_at_5_years"]

# oz_av/in^2 -> kg/m^2. Raw BMI = (weight_oz / height_in^2) * 703 (imperial
# formula with oz instead of lbs). Since 1 lb = 16 oz, raw values are 16x too
# large; divide by 16 to get standard kg/m^2.
BMI_RAW_TO_KG_M2 = 1.0 / 16.0

_ICD_ONLY_CONDITIONS = ["Hypertension", "Dyslipidemia", "Microalbuminuria"]
_COND_SUFFIXES = ["_diagnosis", "_2yr", "_5yr"]

_SDOH_COLLAPSE_TOP_N = [
    "socio_education_level_parents_guardian",
    "socio_employment_status_parents_guardian",
    "socio_financial_strain",
    "socio_insurance_status",
    "socio_social_family_support",
]

# SDOH columns to convert from categorical -> binary (positive/negative)
_SDOH_BINARIZE = {
    # ---- Physical Activity -> 1 = Active, 0 = Inactive ----
    "socio_physical_activity": {
        "new_col": "socio_physical_activity_binary",
        "method": "keyword",
        "inactive_keywords": [
            "sedentary", "inactive", "no exercise", "not exercise",
            "does not exercise", "not physically active", "not active",
            "not currently active", "none", "no extracurricular",
            "not interested", "does not engage", "not involved in clubs",
            "not involved in sports", "not involved in extracurricular",
            "0 days/week", "0 times per week", "no regular exercise",
            "does not participate", "not currently involved",
            "stopped exercising", "not on file", "none reported",
            "low - mostly stays home", "low - primarily sedentary",
            "low - no extracurricular", "low - no interest",
            "low activity; 1/10", "low (lacks motivation",
            "limited - plays video games", "limited - watching tv",
            "limited - homebody", "limited - mostly at home",
            "sedentary/no exercise", "sedentary/very limited",
            "sedentary/limited", "minimal/sedentary", "minimal/none",
            "none/inactive", "inactive/sedentary",
            "previously active", "previously highly active",
            "previously started", "previously swimming",
            "previously participated", "currently no regular",
            "currently reduced", "currently avoids",
            "no:", "little to no regular",
        ],
        "active_keywords": [
            "active", "sport", "football", "basketball", "soccer",
            "baseball", "softball", "volleyball", "tennis", "golf",
            "track", "swim", "dance", "cheer", "gym", "exercise",
            "workout", "work out", "working out", "lifting",
            "weight", "run", "jog", "walk", "bike", "bik",
            "bicycle", "karate", "boxing", "yoga", "zumba",
            "kickbox", "wrestling", "rowing", "cross country",
            "gymnastics", "martial", "mma", "pe ", "p.e.",
            "rotc", "jrotc", "band", "marching", "color guard",
            "colorguard", "plays ", "playing ", "regular",
            "daily", "weekly", "times per week", "days/week",
            "x/week", "x per week", "days per week", "minutes",
            "hour", "5 times", "7 times", "4-5x", "3x", "2-3",
            "3-4", "4x", "5x", "5-6", "5-7",
            "high", "very active", "highly active", "athlete",
            "physically active", "incorporated exercise",
            "increased physical", "increasing", "exercising",
            "treadmill", "elliptical", "cardio", "aerobic",
            "jump rope", "trampoline", "skateboard", "skate",
            "outside", "park", "recess", "conditioning",
            "power lifting", "powerlifting", "shot put", "discus",
            "choir", "orchestra", "theater", "theatre",
        ],
        "default": np.nan,
    },

    # ---- Social/Family Support -> 1 = Adequate+, 0 = Limited/None ----
    "socio_social_family_support": {
        "new_col": "socio_social_family_support_binary",
        "method": "exact",
        "positive": ["Adequate", "Strong", "Excellent",
                     "Family, Friends/peers",
                     "Extended family, family and friends/peers",
                     "Family, Friends/peers, School",
                     "Limited to Adequate"],
        "negative": ["Limited", "None", "Minimal"],
    },

    # ---- Financial Strain -> 1 = At Risk, 0 = Low Risk ----
    "socio_financial_strain": {
        "new_col": "socio_financial_strain_binary",
        "method": "exact",
        "positive": ["Moderate Risk", "High Risk", "Severe", "Medium Risk"],
        "negative": ["Low Risk"],
    },

    # ---- Parental Employment -> 1 = Employed, 0 = Not Employed ----
    "socio_employment_status_parents_guardian": {
        "new_col": "socio_parental_employment_binary",
        "method": "keyword",
        "active_keywords": ["employed", "both employed", "student"],
        "inactive_keywords": ["unemployed", "disabled", "retired",
                              "mixed"],
        "default": np.nan,
    },

    # ---- Parental Education -> 1 = HS or higher, 0 = Below HS ----
    "socio_education_level_parents_guardian": {
        "new_col": "socio_parental_education_binary",
        "method": "exact",
        "positive": ["High School", "Some College", "College",
                     "Graduate", "Post Graduate", "High School/College",
                     "Some College (mother); Graduate (father)",
                     "High School (Mother), Some College (Father)",
                     "Mother: Some College, Father: High School",
                     "Mother: College, Father: High School",
                     "Mother: Some College; Father: College",
                     "Mother: High School; Father: Some College",
                     "Mother: College; Father: High School",
                     "Mother: High School, Father: Some College",
                     "Mother: Some College; Father: High School",
                     "Mother: High School; Father: Some College; Primary caregiver (grandmother): Some College",
                     ],
        "negative": ["Elementary",
                     "Some High School",
                     "Mother: Elementary, Father: High School",
                     "Mother: Some High School (9th Grade); Father: High School (12th Grade)",
                     "Mother: High School; Father: Elementary",
                     "Mother: High School (incomplete, grade 9); Father: Some College",
                     "Some College (Mother), Elementary (Father)",
                     "Mother: High School, Father: Elementary",
                     ],
        # "Unknown" -> NaN
    },

    # ---- Insurance Status -> categorical: Private, Government, Uninsured ----
    "socio_insurance_status": {
        "new_col": "socio_insurance_category",
        "method": "exact_categorical",
        "mapping": {
            "Private": "Private",
            "Multiple": "Private",
            "Medicaid": "Government",
            "CHIP": "Government",
            "TRICARE WEST": "Government",
            "Medicare": "Government",
            "Uninsured": "Uninsured",
            "Self-Pay": "Uninsured",
        },
    },
}

DEFAULT_TOP_N = 5


def convert_bmi_to_standard(df, inplace=False):
    """Convert BMI columns from oz_av/in^2 to kg/m^2."""
    if not inplace:
        df = df.copy()
    for col in _BMI_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce") * BMI_RAW_TO_KG_M2
    return df


def drop_icd_only_conditions(df, inplace=False):
    """Remove ICD-code-only condition columns; OUTCOME_* versions are kept."""
    if not inplace:
        df = df.copy()
    cols_to_drop = [
        f"{cond}{suffix}"
        for cond in _ICD_ONLY_CONDITIONS
        for suffix in _COND_SUFFIXES
        if f"{cond}{suffix}" in df.columns
    ]
    if cols_to_drop:
        df.drop(columns=cols_to_drop, inplace=True)
    return df


def collapse_sdoh_categories(df, top_n=DEFAULT_TOP_N, columns=None, inplace=False):
    """Keep top-N most frequent categories per SDOH column; rest -> 'Other'."""
    if not inplace:
        df = df.copy()
    if columns is None:
        columns = _SDOH_COLLAPSE_TOP_N
    for col in columns:
        if col not in df.columns:
            continue
        top_cats = df[col].value_counts(dropna=True).head(top_n).index.tolist()
        keep_mask = df[col].isin(top_cats) | df[col].isna()
        df.loc[~keep_mask, col] = "Other"
    return df


def _binarize_sdoh(df, config=None, inplace=False):
    """Convert high-cardinality SDOH categoricals to binary (1/0) or mapped
    categorical columns. Original column KEPT; new column added."""
    if not inplace:
        df = df.copy()
    if config is None:
        config = _SDOH_BINARIZE

    for orig_col, spec in config.items():
        if orig_col not in df.columns:
            continue

        new_col = spec["new_col"]
        method = spec["method"]
        series = df[orig_col]

        if method == "exact":
            pos_set = set(spec.get("positive", []))
            neg_set = set(spec.get("negative", []))
            df[new_col] = np.where(
                series.isin(pos_set), 1,
                np.where(series.isin(neg_set), 0, np.nan)
            )

        elif method == "keyword":
            active_kw = [k.lower() for k in spec.get("active_keywords", [])]
            inactive_kw = [k.lower() for k in spec.get("inactive_keywords", [])]
            default = spec.get("default", np.nan)

            result = pd.Series(default, index=df.index, dtype=float)

            for idx, val in series.items():
                if pd.isna(val):
                    continue
                val_lower = str(val).lower()
                if any(kw in val_lower for kw in inactive_kw):
                    result.at[idx] = 0
                    continue
                if any(kw in val_lower for kw in active_kw):
                    result.at[idx] = 1
                    continue

            df[new_col] = result

        elif method == "exact_categorical":
            mapping = spec.get("mapping", {})
            df[new_col] = series.map(mapping)

        # Log distribution
        n_valid = df[new_col].notna().sum()
        if method == "exact_categorical":
            dist = df[new_col].value_counts(dropna=True)
            dist_str = ", ".join(f"{v}={c}" for v, c in dist.items())
            n_unk = df[orig_col].notna().sum() - n_valid
            print(f"    {new_col}: {dist_str}, unmatched={n_unk}, missing={len(df)-df[orig_col].notna().sum()}")
        else:
            n_pos = (df[new_col] == 1).sum()
            n_neg = (df[new_col] == 0).sum()
            n_unk = df[orig_col].notna().sum() - n_valid
            print(f"    {new_col}: 1={n_pos}, 0={n_neg}, unmatched={n_unk}, missing={len(df)-df[orig_col].notna().sum()}")

    return df


def preprocess(df, convert_bmi=True, drop_icd_conditions=True,
               collapse_sdoh=True, binarize_sdoh_cats=True,
               top_n_cats=DEFAULT_TOP_N,
               sdoh_columns=None, inplace=False):
    """Run all preprocessing steps."""
    if not inplace:
        df = df.copy()

    n_cols_before = len(df.columns)

    if convert_bmi:
        df = convert_bmi_to_standard(df, inplace=True)
        print(f"  [preprocess] BMI converted to kg/m^2  (/ 16, raw was oz-based imperial)")

    if drop_icd_conditions:
        n_before = len(df.columns)
        df = drop_icd_only_conditions(df, inplace=True)
        print(f"  [preprocess] Dropped {n_before - len(df.columns)} ICD-only condition columns")

    if binarize_sdoh_cats:
        df = _binarize_sdoh(df, inplace=True)
        print(f"  [preprocess] SDOH categoricals binarized (new binary columns added)")

    if collapse_sdoh:
        df = collapse_sdoh_categories(df, top_n=top_n_cats, columns=sdoh_columns, inplace=True)
        print(f"  [preprocess] Remaining SDOH categoricals collapsed to top-{top_n_cats} + Other")

    print(f"  [preprocess] Done. Columns: {n_cols_before} -> {len(df.columns)}")
    return df


# ============================================================================
# LOAD & PREPROCESS
# ============================================================================

print("Loading dataset...", end="")
df_full = Dataset.get("t2d_outcomes").read_table(format="pandas")
print(f" OK  ({len(df_full):,} patients, {len(df_full.columns)} columns)")

print("\nRunning preprocessing...")
df_full = preprocess(df_full, top_n_cats=5)

print(f"\nOK df_full ready: {len(df_full):,} rows x {len(df_full.columns)} columns")


#### **************************************************************************
### The four TableOne blocks (GROUP in {sex, covid_pre_post, age_cat}, each with
### a continuous [median/IQR] table and a categorical [n %] table), the
### statsmodels mixed-effects model (a1c ~ C(period)*C(sex)*year, random
### intercept+slope per mrn, REML), and the trajectory plot follow here exactly
### as authored. See REPRODUCE_SEX_COVID_ANALYSES.md for the required export
### aliases and the pval=True / no-hard-coded-means changes to apply on re-run.
#### **************************************************************************
