from __future__ import annotations

from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import pandas as pd

from false_research_agent.schemas.study_design import StudyDesign


def generate_plots(design: StudyDesign, data: pd.DataFrame, output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: List[Path] = []

    for dv in design.dependent_variables:
        pre_col = f"{dv}_pre"
        post_col = f"{dv}_post"
        if pre_col not in data.columns or post_col not in data.columns:
            continue

        working = data[["group", pre_col, post_col]].copy()
        working = working.dropna(subset=[pre_col, post_col])
        working["gain"] = working[post_col] - working[pre_col]

        fig, ax = plt.subplots(figsize=(6.5, 4.0))
        groups = [working[working["group"] == label]["gain"] for label in design.group_labels]
        ax.boxplot(groups, labels=design.group_labels, showmeans=True)
        ax.set_title(f"Gain scores: {dv}")
        ax.set_xlabel("Group")
        ax.set_ylabel("Post - Pre")
        ax.grid(axis="y", alpha=0.2)

        filename = f"plot_{dv}_gain.png".replace(" ", "_")
        path = output_dir / filename
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        plot_paths.append(path)

    return plot_paths
