from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from core.utils import write_json


NOISE = "zxqv_@@@_CORRUPTED_VECTOR_NOISE_9f8e7d_###_zxqv"


def _rebuild_embedding_text(row: pd.Series) -> str:
    published = pd.to_datetime(row.get("published"), utc=True, errors="coerce")
    published_text = published.date().isoformat() if not pd.isna(published) else ""
    return "\n".join([
        f"Title: {row.get('title', '')}",
        f"Authors: {row.get('authors_joined', '')}",
        f"Published: {published_text}",
        f"Categories: {row.get('categories_joined', '')}",
        f"Summary: {row.get('summary', '')}",
    ])


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six deterministic data-corruption scenarios and write an audit log.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    required = {"paper_id", "title", "summary", "published", "age_days", "text_for_embedding"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Cannot corrupt dataframe; missing columns: {', '.join(missing)}")
    if len(df) < 10:
        raise ValueError("At least 10 rows are required for the six corruption scenarios")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    corrupted["published"] = pd.to_datetime(corrupted["published"], utc=True, errors="coerce")
    corrupted = corrupted.sort_values("published", ascending=False).reset_index(drop=True)
    original_rows = len(corrupted)
    actions: list[dict] = []

    # 1) Remove the newest 20% to simulate a source that silently stopped updating.
    drop_count = max(1, math.ceil(original_rows * 0.20))
    dropped = corrupted.iloc[:drop_count]
    actions.append({
        "scenario": "drop_latest_records",
        "description": "Removed the newest 20% of records.",
        "affected_count": int(drop_count),
        "paper_ids": dropped["paper_id"].astype(str).tolist(),
    })
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)

    # Deterministic slices make repeated demonstrations reproducible.
    mutation_count = max(2, math.ceil(len(corrupted) * 0.15))
    blank_idx = list(range(0, min(mutation_count, len(corrupted))))
    noise_idx = list(range(mutation_count, min(2 * mutation_count, len(corrupted))))
    title_idx = list(range(2 * mutation_count, min(3 * mutation_count, len(corrupted))))

    # 2) Blank summaries and keep summary_chars consistent with the damage.
    corrupted.loc[blank_idx, "summary"] = ""
    if "summary_chars" in corrupted:
        corrupted.loc[blank_idx, "summary_chars"] = 0
    actions.append({
        "scenario": "blank_summary",
        "description": "Replaced summaries with empty strings.",
        "affected_count": len(blank_idx),
        "paper_ids": corrupted.loc[blank_idx, "paper_id"].astype(str).tolist(),
    })

    # 3) Noise is attached after the structured embedding text is rebuilt below.
    noise_ids = corrupted.loc[noise_idx, "paper_id"].astype(str).tolist()
    actions.append({
        "scenario": "inject_text_noise",
        "description": "Injected a deterministic garbage token sequence into text_for_embedding.",
        "affected_count": len(noise_idx),
        "paper_ids": noise_ids,
        "noise": NOISE,
    })

    # 4) Force visibly invalid titles shorter than ten characters.
    original_titles = corrupted.loc[title_idx, ["paper_id", "title"]].copy()
    corrupted.loc[title_idx, "title"] = corrupted.loc[title_idx, "title"].astype(str).str[:7]
    actions.append({
        "scenario": "truncate_title",
        "description": "Truncated titles to at most 7 characters.",
        "affected_count": len(title_idx),
        "records": [
            {"paper_id": str(row.paper_id), "original_title": str(row.title)}
            for row in original_titles.itertuples(index=False)
        ],
    })

    # 5) Make enough records stale for the >25% Freshness SLA to trip.
    stale_count = max(1, math.ceil(len(corrupted) * 0.35))
    stale_idx = list(range(stale_count))
    stale_before = corrupted.loc[stale_idx, ["paper_id", "published"]].copy()
    corrupted.loc[stale_idx, "published"] = (
        corrupted.loc[stale_idx, "published"] - pd.DateOffset(years=5)
    )
    corrupted.loc[stale_idx, "age_days"] = (
        pd.to_numeric(corrupted.loc[stale_idx, "age_days"], errors="coerce").fillna(0) + 1826
    ).astype(int)
    actions.append({
        "scenario": "stale_date",
        "description": "Moved publication dates five years into the past.",
        "affected_count": len(stale_idx),
        "records": [
            {"paper_id": str(row.paper_id), "original_published": row.published.isoformat()}
            for row in stale_before.itertuples(index=False)
        ],
    })

    # Rebuild structured content so blank summaries, titles and dates propagate.
    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_embedding_text, axis=1)
    corrupted.loc[noise_idx, "text_for_embedding"] = (
        corrupted.loc[noise_idx, "text_for_embedding"].astype(str) + "\nNoise: " + NOISE
    )

    # 6) Duplicate already damaged rows, preserving paper_id to violate uniqueness.
    duplicate_count = max(2, math.ceil(len(corrupted) * 0.15))
    duplicated = corrupted.iloc[:duplicate_count].copy(deep=True)
    corrupted = pd.concat([corrupted, duplicated], ignore_index=True)
    actions.append({
        "scenario": "duplicate_rows",
        "description": "Appended exact row copies with duplicate paper_id values.",
        "affected_count": int(duplicate_count),
        "paper_ids": duplicated["paper_id"].astype(str).tolist(),
    })

    log = {
        "original_rows": int(original_rows),
        "corrupted_rows": int(len(corrupted)),
        "scenario_count": len(actions),
        "actions": actions,
    }
    write_json(Path(output_log_path), log)
    return corrupted.reset_index(drop=True)
