from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EffectSize(BaseModel):
    name: str = Field(...)
    value: float = Field(...)


class TestResult(BaseModel):
    test_name: str = Field(...)
    statistic: float = Field(...)
    p_value: float = Field(...)
    df: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None


class AnalysisResult(BaseModel):
    method: str = Field(...)
    outcome: str = Field(...)
    primary_result: TestResult
    effect_sizes: List[EffectSize] = Field(default_factory=list)
    model_summary: Optional[str] = None
    group_means: Optional[Dict[str, float]] = None
