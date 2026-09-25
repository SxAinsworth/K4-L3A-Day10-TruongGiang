from __future__ import annotations

from datetime import UTC, datetime
import json

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    payload = json.loads(df.to_json(orient="records", date_format="iso"))
    write_json(json_path, payload)


def main() -> None:
    """Run corruption, evaluation, idempotent repair, and comparison reporting.

    Pseudo-code:
    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate.
    5. Run quality checks/freshness tren corrupted data.
    6. Repair lai tu raw records.
    7. Evaluate repaired dataset.
    8. Tao comparison report.
    """
    settings = load_settings()
    if not settings.paths.baseline_metrics.exists():
        raise FileNotFoundError("Baseline metrics are missing; run python script/run_phase1.py first")
    if not settings.paths.clean_json.exists():
        raise FileNotFoundError("Clean dataset is missing; run python script/run_phase1.py first")
    if not settings.paths.eval_testset.exists():
        raise FileNotFoundError("Benchmark test set is missing; run python script/run_phase1.py first")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = pd.read_json(settings.paths.clean_json)

    print("[1/8] Injecting six corruption scenarios...")
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    _save_dataframe(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json,
    )

    print("[2/8] Running quality gate on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")

    print("[3/8] Building corrupted Chroma collection...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        settings.paths.corrupted_embeddings_json,
    )

    print("[4/8] Measuring corrupted RAG performance...")
    corrupted_evaluation = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )

    print("[5/8] Repairing clean data from preserved raw records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, datetime.now(UTC))
    _save_dataframe(
        repaired_df,
        settings.paths.repaired_clean_csv,
        settings.paths.repaired_clean_json,
    )

    print("[6/8] Validating and indexing repaired data...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    if not repaired_quality["success"]:
        raise RuntimeError("Repaired data failed the quality gate")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        settings.paths.repaired_embeddings_json,
    )

    print("[7/8] Measuring repaired RAG performance...")
    repaired_evaluation = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )

    print("[8/8] Writing comparison report...")
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_evaluation.summary,
        repaired_evaluation.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_quality["freshness"],
        repaired_quality["freshness"],
    )

    print("\nMetric                 Baseline   Corrupted   Repaired")
    print("---------------------  --------   ---------   --------")
    for label, key in (
        ("Retrieval Hit Rate", "retrieval_hit_rate"),
        ("Mean Token F1", "mean_token_f1"),
        ("Judge Accuracy", "judge_accuracy"),
        ("Mean Judge Score", "mean_judge_score"),
    ):
        print(
            f"{label:<21}  {baseline_metrics[key]:>8.4f}   "
            f"{corrupted_evaluation.summary[key]:>9.4f}   {repaired_evaluation.summary[key]:>8.4f}"
        )
    print(f"\nCorrupted quality gate: {corrupted_quality['success']}")
    print(f"Repaired quality gate: {repaired_quality['success']}")
    print(f"Report: {settings.paths.comparison_report}")
