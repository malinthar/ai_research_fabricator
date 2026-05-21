from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

from false_research_agent.schemas.analysis_result import AnalysisResult, EffectSize, TestResult
from false_research_agent.schemas.study_design import StudyDesign


def run_analysis(design: StudyDesign, data: pd.DataFrame) -> List[AnalysisResult]:
    results: List[AnalysisResult] = []

    for dv in design.dependent_variables:
        pre_col = f"{dv}_pre"
        post_col = f"{dv}_post"
        if pre_col not in data.columns or post_col not in data.columns:
            raise ValueError(f"Missing expected columns for {dv}")

        working = data[["group", pre_col, post_col, *design.covariates]].copy()
        working = working.dropna(subset=[pre_col, post_col])
        working["gain"] = working[post_col] - working[pre_col]
        outcome_label = f"{dv}_gain"

        if design.analysis_method == "t-test":
            result = _run_t_test(working, outcome_label, design.group_labels)
        elif design.analysis_method == "ANOVA":
            result = _run_anova(working, outcome_label, design.group_labels)
        elif design.analysis_method == "linear_regression":
            result = _run_regression(working, outcome_label, design.covariates)
        else:
            raise ValueError(f"Unsupported analysis method: {design.analysis_method}")

        results.append(result)

    return results


def _run_t_test(df: pd.DataFrame, outcome: str, group_labels: list[str]) -> AnalysisResult:
    if len(group_labels) < 2:
        raise ValueError("t-test requires at least two groups")

    group_a = df[df["group"] == group_labels[0]]["gain"].to_numpy()
    group_b = df[df["group"] == group_labels[1]]["gain"].to_numpy()

    stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False, nan_policy="omit")
    mean_diff = float(np.nanmean(group_b) - np.nanmean(group_a))
    ci_low, ci_high, df_value = _welch_ci(group_a, group_b)

    d_value = _cohens_d(group_a, group_b)

    primary = TestResult(
        test_name="Welch t-test",
        statistic=float(stat),
        p_value=float(p_value),
        df=float(df_value),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
    )

    return AnalysisResult(
        method="t-test",
        outcome=outcome,
        primary_result=primary,
        effect_sizes=[EffectSize(name="cohens_d", value=float(d_value))],
        group_means={
            group_labels[0]: float(np.nanmean(group_a)),
            group_labels[1]: float(np.nanmean(group_b)),
        },
    )


def _run_anova(df: pd.DataFrame, outcome: str, group_labels: list[str]) -> AnalysisResult:
    grouped = [df[df["group"] == label]["gain"].to_numpy() for label in group_labels]
    stat, p_value = stats.f_oneway(*grouped)

    eta_sq = _eta_squared(df, group_labels)
    means = {label: float(np.nanmean(df[df["group"] == label]["gain"])) for label in group_labels}

    primary = TestResult(
        test_name="One-way ANOVA",
        statistic=float(stat),
        p_value=float(p_value),
        df=float(len(group_labels) - 1),
    )

    return AnalysisResult(
        method="ANOVA",
        outcome=outcome,
        primary_result=primary,
        effect_sizes=[EffectSize(name="eta_squared", value=float(eta_sq))],
        group_means=means,
    )


def _run_regression(df: pd.DataFrame, outcome: str, covariates: list[str]) -> AnalysisResult:
    predictors = ["C(group)"] + covariates
    formula = f"gain ~ {' + '.join(predictors)}"
    model = smf.ols(formula=formula, data=df).fit()

    anova = anova_lm(model, typ=2)
    group_row = anova.loc["C(group)"]

    primary = TestResult(
        test_name="OLS group effect",
        statistic=float(group_row["F"]),
        p_value=float(group_row["PR(>F)"]),
        df=float(group_row["df"]),
    )

    return AnalysisResult(
        method="linear_regression",
        outcome=outcome,
        primary_result=primary,
        effect_sizes=[EffectSize(name="r_squared", value=float(model.rsquared))],
        model_summary=model.summary().as_text(),
    )


def _welch_ci(group_a: np.ndarray, group_b: np.ndarray) -> tuple[float, float, float]:
    mean_a = np.nanmean(group_a)
    mean_b = np.nanmean(group_b)
    var_a = np.nanvar(group_a, ddof=1)
    var_b = np.nanvar(group_b, ddof=1)
    n_a = np.sum(~np.isnan(group_a))
    n_b = np.sum(~np.isnan(group_b))

    se = np.sqrt(var_a / n_a + var_b / n_b)
    df = (var_a / n_a + var_b / n_b) ** 2 / (
        (var_a**2) / (n_a**2 * (n_a - 1)) + (var_b**2) / (n_b**2 * (n_b - 1))
    )
    t_crit = stats.t.ppf(0.975, df)
    diff = mean_b - mean_a
    return diff - t_crit * se, diff + t_crit * se, float(df)


def _cohens_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    mean_a = np.nanmean(group_a)
    mean_b = np.nanmean(group_b)
    var_a = np.nanvar(group_a, ddof=1)
    var_b = np.nanvar(group_b, ddof=1)
    pooled_sd = np.sqrt((var_a + var_b) / 2)
    if pooled_sd == 0:
        return 0.0
    return float((mean_b - mean_a) / pooled_sd)


def _eta_squared(df: pd.DataFrame, group_labels: list[str]) -> float:
    overall_mean = float(np.nanmean(df["gain"]))
    ss_between = 0.0
    ss_total = float(np.nansum((df["gain"] - overall_mean) ** 2))

    for label in group_labels:
        group_vals = df[df["group"] == label]["gain"]
        group_mean = float(np.nanmean(group_vals))
        n_group = int(np.sum(~np.isnan(group_vals)))
        ss_between += n_group * (group_mean - overall_mean) ** 2

    if ss_total == 0:
        return 0.0

    return float(ss_between / ss_total)
