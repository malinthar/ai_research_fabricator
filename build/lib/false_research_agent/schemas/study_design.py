from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class StudyDesign(BaseModel):
    study_type: str = Field(..., examples=["randomized controlled trial"])
    sample_size: int = Field(..., ge=40, le=2000)
    duration_weeks: int = Field(..., ge=2, le=52)
    participants: str = Field(...)
    independent_variable: str = Field(...)
    dependent_variables: List[str] = Field(..., min_length=1)
    analysis_method: Literal["t-test", "ANOVA", "linear_regression"] = Field(...)
    covariates: List[str] = Field(default_factory=list)
    group_labels: List[str] = Field(default_factory=lambda: ["control", "treatment"])

    @field_validator("group_labels")
    @classmethod
    def validate_groups(cls, value: List[str]) -> List[str]:
        if len(value) < 2:
            raise ValueError("group_labels must include at least two groups")
        return value
