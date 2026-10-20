"""Reproducible end-to-end synthetic-only run and report persistence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .benchmark import benchmark
from .cohort import synthetic_cohort
from .dashboard import benchmark_html
from .io import atomic_json
from .schema import ValidationError


def synthetic_experiment(output: Path, *, n_subjects: int = 24, trials: int = 30,
                         seed: int = 2026, missing_rate: float = 0.12, reps: int = 300) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise ValidationError("Output directory must be empty to avoid destroying or mixing prior scientific runs")
    result = benchmark(synthetic_cohort(n_subjects=n_subjects, trials_per_subject=trials,
                                        seed=seed, missing_rate=missing_rate), seed=seed, reps=reps, source_kind="synthetic")
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / "benchmark.json", result)
    (output / "index.html").write_text(benchmark_html(result), encoding="utf-8")
    return result
