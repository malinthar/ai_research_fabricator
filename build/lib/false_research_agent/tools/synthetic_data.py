from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from false_research_agent.config import DataConfig
from false_research_agent.schemas.study_design import StudyDesign


@dataclass(frozen=True)
class SyntheticDataArtifacts:
    dataframe: pd.DataFrame
    metadata: dict


def generate_synthetic_data(design: StudyDesign, config: DataConfig) -> SyntheticDataArtifacts:
    rng = np.random.default_rng(config.seed)
    sample_size = design.sample_size
    group_labels = design.group_labels

    assignments = rng.choice(group_labels, size=sample_size, replace=True)
    ability = rng.normal(loc=0.0, scale=1.0, size=sample_size)
    engagement = 0.6 * ability + rng.normal(0.0, 0.8, size=sample_size)

    covariate_frame = _build_covariates(design.covariates, sample_size, rng)

    data = {
        "participant_id": np.arange(1, sample_size + 1),
        "group": assignments,
        "engagement_latent": engagement,
        **covariate_frame,
    }

    for dv in design.dependent_variables:
        pre_mean = 50 + 8 * ability
        pre_score = pre_mean + rng.normal(0.0, config.noise_sd, size=sample_size)

        treatment_effect = _treatment_effect(assignments, group_labels)
        time_effect = rng.normal(2.0, 1.0, size=sample_size)
        post_score = pre_score + time_effect + treatment_effect + rng.normal(0.0, config.noise_sd, size=sample_size)

        data[f"{dv}_pre"] = pre_score
        data[f"{dv}_post"] = post_score

    dropout_mask = rng.random(sample_size) < config.dropout_rate
    data["dropped_out"] = dropout_mask

    for dv in design.dependent_variables:
        data[f"{dv}_post"] = np.where(dropout_mask, np.nan, data[f"{dv}_post"])

    df = pd.DataFrame(data)
    metadata = {
        "seed": config.seed,
        "dropout_rate": config.dropout_rate,
        "noise_sd": config.noise_sd,
        "sample_size": sample_size,
    }

    return SyntheticDataArtifacts(dataframe=df, metadata=metadata)


def _build_covariates(names: Iterable[str], size: int, rng: np.random.Generator) -> dict:
    covariates: dict[str, np.ndarray] = {}
    for name in names:
        lowered = name.lower()
        if "age" in lowered:
            covariates[name] = rng.normal(20.0, 2.0, size=size)
        elif "gpa" in lowered:
            covariates[name] = np.clip(rng.normal(3.2, 0.4, size=size), 0.0, 4.0)
        elif "semester" in lowered or "year" in lowered:
            covariates[name] = rng.integers(1, 5, size=size)
        else:
            covariates[name] = rng.normal(0.0, 1.0, size=size)
    return covariates


def _treatment_effect(assignments: np.ndarray, group_labels: list[str]) -> np.ndarray:
    if len(group_labels) < 2:
        return np.zeros(assignments.shape[0])

    control = group_labels[0]
    treatment = group_labels[1]
    effect = np.where(assignments == treatment, 4.5, 0.0)
    return effect
