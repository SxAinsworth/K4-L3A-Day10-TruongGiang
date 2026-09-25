from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    if report_name == "baseline":
        return settings.paths.baseline_quality_report
    if report_name == "corrupted":
        return settings.paths.corrupted_quality_report
    return settings.paths.quality_dir / f"{report_name}_quality_report.json"


def _expectation_summary(validation_result: Any) -> list[dict[str, Any]]:
    raw_results = getattr(validation_result, "results", [])
    summaries: list[dict[str, Any]] = []
    for result in raw_results:
        if isinstance(result, dict):
            config = result.get("expectation_config", {})
            success = result.get("success", False)
            statistics = result.get("result", {})
        else:
            config = getattr(result, "expectation_config", {})
            success = getattr(result, "success", False)
            statistics = getattr(result, "result", {})
        if hasattr(config, "to_json_dict"):
            config = config.to_json_dict()
        summaries.append(
            {
                "expectation_type": config.get("type", "unknown"),
                "success": bool(success),
                "statistics": statistics,
            }
        )
    return summaries


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the GX 1.x quality gate and persist a compact JSON report.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    try:
        import great_expectations as gx
        import great_expectations.expectations as gxe
    except ImportError as exc:
        raise RuntimeError(
            "Great Expectations is required for data quality checks. "
            "Install project dependencies before running the quality gate."
        ) from exc

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    expectation_suite = gx.ExpectationSuite(name=f"{report_name}_quality_suite")
    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="title"),
        gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    for expectation in expectations:
        expectation_suite.add_expectation(expectation)

    validation_result = batch.validate(expectation_suite)
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    report = {
        "success": bool(validation_result.success),
        "report_name": report_name,
        "row_count": int(len(df)),
        "expectations": _expectation_summary(validation_result),
        "freshness": freshness,
    }
    write_json(_quality_report_path(settings, report_name), report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist the freshness summary for a cleaned dataframe.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    total_rows = int(len(df))
    age_days = pd.to_numeric(df.get("age_days", pd.Series(dtype="float64")), errors="coerce")
    stale_rows = int((age_days > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    published = pd.to_datetime(df.get("published", pd.Series(dtype="object")), errors="coerce")
    valid_published = published.dropna()
    report = {
        "latest_published": valid_published.max().date().isoformat() if not valid_published.empty else None,
        "oldest_published": valid_published.min().date().isoformat() if not valid_published.empty else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "is_fresh": bool(total_rows > 0 and stale_ratio <= 0.25),
    }
    write_json(Path(report_path), report)
    return report
