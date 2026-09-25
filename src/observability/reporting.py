from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline metrics and data-quality results as Markdown.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source and Index",
        "",
        f"- Source: {source_summary.get('source', 'unknown')}",
        f"- Raw records: {source_summary.get('records', 0)}",
        f"- Clean rows: {source_summary.get('clean_rows', 0)}",
        f"- Embedding model: {source_summary.get('embedding_model', 'unknown')}",
        f"- Collection: {source_summary.get('collection_name', 'unknown')}",
        "",
        "## Baseline Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        lines.append(f"| `{key}` | {metrics.get(key, 'N/A')} |")
    lines.extend(
        [
            "",
            "## Data Quality",
            "",
            f"- Quality gate success: `{quality.get('success', False)}`",
            f"- Rows checked: `{quality.get('row_count', 0)}`",
            f"- Freshness: `{freshness.get('is_fresh', False)}`",
            f"- Stale rows: `{freshness.get('stale_rows', 0)}/{freshness.get('total_rows', 0)}`",
            f"- Stale ratio: `{freshness.get('stale_ratio', 0.0):.3f}`",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
