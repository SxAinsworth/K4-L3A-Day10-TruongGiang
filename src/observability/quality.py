from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the Great Expectations gate plus freshness SLA and persist results.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="title"),
        gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    results = [batch.validate(expectation) for expectation in expectations]
    serialized = [result.to_json_dict() for result in results]
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    success = all(bool(result.success) for result in results) and freshness["is_fresh"]
    report = {
        "report_name": report_name,
        "success": success,
        "statistics": {
            "evaluated_expectations": len(results),
            "successful_expectations": sum(bool(result.success) for result in results),
            "unsuccessful_expectations": sum(not bool(result.success) for result in results),
            "success_percent": 100.0 * sum(bool(result.success) for result in results) / len(results),
        },
        "freshness": freshness,
        "results": serialized,
    }
    lowered = report_name.lower()
    if "corrupt" in lowered:
        report_path = settings.paths.corrupted_quality_report
    elif lowered in {"baseline", "test"}:
        report_path = settings.paths.baseline_quality_report
    else:
        report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    write_json(report_path, report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication freshness and persist its SLA status.

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
    published_values = df["published"] if "published" in df else pd.Series(index=df.index, dtype="object")
    age_values = df["age_days"] if "age_days" in df else pd.Series(index=df.index, dtype="float64")
    published = pd.to_datetime(published_values, utc=True, errors="coerce")
    ages = pd.to_numeric(age_values, errors="coerce")
    valid_ages = ages.dropna()
    total_rows = int(len(df))
    stale_rows = int((valid_ages > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    valid_published = published.dropna()
    report = {
        "latest_published": valid_published.max().date().isoformat() if not valid_published.empty else None,
        "oldest_published": valid_published.min().date().isoformat() if not valid_published.empty else None,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": total_rows > 0 and stale_ratio <= 0.25,
    }
    write_json(Path(report_path), report)
    return report
