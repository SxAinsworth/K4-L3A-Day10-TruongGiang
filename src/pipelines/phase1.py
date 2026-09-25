from __future__ import annotations

from datetime import UTC, datetime
import json

from core.config import load_settings
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run the clean baseline pipeline end to end.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    settings = load_settings()
    print("[1/7] Loading source records...")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    print("[2/7] Cleaning data...")
    clean_df = build_clean_dataframe(records, datetime.now(UTC))
    if clean_df.empty:
        raise RuntimeError("Cleaning produced no valid records")
    write_csv(clean_df, settings.paths.clean_csv)
    clean_payload = json.loads(clean_df.to_json(orient="records", date_format="iso"))
    write_json(settings.paths.clean_json, clean_payload)

    print("[3/7] Running Great Expectations quality gate...")
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    if not quality["success"]:
        raise RuntimeError(
            "Data quality gate failed; inspect "
            f"{settings.paths.baseline_quality_report} before indexing"
        )

    print("[4/7] Creating/loading benchmark test set...")
    test_set = load_or_create_test_set(clean_df, settings)

    print("[5/7] Building ChromaDB vector index...")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)

    print("[6/7] Evaluating baseline retrieval and QA...")
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    print("[7/7] Writing Phase 1 report...")
    source_summary = {
        "source": settings.source_api,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "indexed_documents": index.collection.count(),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        quality["freshness"],
    )

    print("\nPhase 1 baseline completed successfully.")
    print(f"Clean rows: {len(clean_df)}")
    print(f"Benchmark questions: {len(test_set)}")
    print(f"Indexed documents: {index.collection.count()}")
    print(f"Retrieval Hit Rate: {evaluation.summary['retrieval_hit_rate']:.4f}")
    print(f"Mean Token F1: {evaluation.summary['mean_token_f1']:.4f}")
    print(f"Report: {settings.paths.baseline_report}")
