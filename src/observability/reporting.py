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
    """Generate the baseline Markdown report from measured artifacts.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    ragas = metrics.get("ragas", {})
    ragas_status = ragas.get("skipped") or ragas.get("error") or "Completed"
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source and dataset",
        "",
        "| Signal | Value |",
        "|---|---:|",
        f"| Source | {source_summary.get('source', 'Crossref REST API')} |",
        f"| Raw records | {source_summary.get('raw_records', 0)} |",
        f"| Clean records | {source_summary.get('clean_records', 0)} |",
        f"| Indexed documents | {source_summary.get('indexed_documents', 0)} |",
        f"| Benchmark questions | {metrics.get('samples', 0)} |",
        "",
        "## Baseline evaluation",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Retrieval Hit Rate | {metrics.get('retrieval_hit_rate', 0):.4f} |",
        f"| Mean Token F1 | {metrics.get('mean_token_f1', 0):.4f} |",
        f"| LLM Judge Accuracy | {metrics.get('judge_accuracy', 0):.4f} |",
        f"| Mean LLM Judge Score | {metrics.get('mean_judge_score', 0):.2f} / 5 |",
        f"| Ragas | {ragas_status} |",
        "",
        "## Data quality gate",
        "",
        "| Signal | Value |",
        "|---|---:|",
        f"| Overall success | {quality.get('success', False)} |",
        f"| Successful expectations | {quality.get('statistics', {}).get('successful_expectations', 0)} |",
        f"| Failed expectations | {quality.get('statistics', {}).get('unsuccessful_expectations', 0)} |",
        "",
        "## Freshness SLA",
        "",
        "| Signal | Value |",
        "|---|---:|",
        f"| Latest publication | {freshness.get('latest_published')} |",
        f"| Oldest publication | {freshness.get('oldest_published')} |",
        f"| Stale rows | {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)} |",
        f"| Stale ratio | {freshness.get('stale_ratio', 0):.2%} |",
        f"| Is fresh | {freshness.get('is_fresh', False)} |",
        "",
        "## Reproducibility",
        "",
        "Run `python script/run_phase1.py` from the project root with the project environment activated.",
        "",
    ]
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
    """Generate a Markdown comparison of baseline, corrupted, and repaired runs."""
    def metric(payload: dict[str, Any], name: str) -> float:
        return float(payload.get(name, 0.0))

    lines = [
        "# Data Corruption and Idempotent Repair Report",
        "",
        "## Baseline vs. corrupted vs. repaired",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "|---|---:|---:|---:|",
        f"| Retrieval Hit Rate | {metric(baseline_metrics, 'retrieval_hit_rate'):.4f} | "
        f"{metric(corrupted_metrics, 'retrieval_hit_rate'):.4f} | {metric(repaired_metrics, 'retrieval_hit_rate'):.4f} |",
        f"| Mean Token F1 | {metric(baseline_metrics, 'mean_token_f1'):.4f} | "
        f"{metric(corrupted_metrics, 'mean_token_f1'):.4f} | {metric(repaired_metrics, 'mean_token_f1'):.4f} |",
        f"| Judge Accuracy | {metric(baseline_metrics, 'judge_accuracy'):.4f} | "
        f"{metric(corrupted_metrics, 'judge_accuracy'):.4f} | {metric(repaired_metrics, 'judge_accuracy'):.4f} |",
        f"| Mean Judge Score | {metric(baseline_metrics, 'mean_judge_score'):.2f} | "
        f"{metric(corrupted_metrics, 'mean_judge_score'):.2f} | {metric(repaired_metrics, 'mean_judge_score'):.2f} |",
        "",
        "## Quality and freshness signals",
        "",
        "| Signal | Corrupted | Repaired |",
        "|---|---:|---:|",
        f"| Quality gate success | {corrupted_quality.get('success', False)} | {repaired_quality.get('success', False)} |",
        f"| Failed expectations | {corrupted_quality.get('statistics', {}).get('unsuccessful_expectations', 0)} | "
        f"{repaired_quality.get('statistics', {}).get('unsuccessful_expectations', 0)} |",
        f"| Freshness SLA | {corrupted_freshness.get('is_fresh', False)} | {repaired_freshness.get('is_fresh', False)} |",
        f"| Stale rows | {corrupted_freshness.get('stale_rows', 0)} / {corrupted_freshness.get('total_rows', 0)} | "
        f"{repaired_freshness.get('stale_rows', 0)} / {repaired_freshness.get('total_rows', 0)} |",
        f"| Stale ratio | {corrupted_freshness.get('stale_ratio', 0):.2%} | "
        f"{repaired_freshness.get('stale_ratio', 0):.2%} |",
        "",
        "## Conclusion",
        "",
        "The corrupted run demonstrates silent quality degradation while the application remains executable. "
        "The repaired run rebuilds clean data and a separate vector collection from preserved raw records, "
        "making the recovery idempotent and reproducible.",
        "",
    ]
    write_text(report_path, "\n".join(lines))
