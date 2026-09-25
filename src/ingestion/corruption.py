from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.utils import write_json


def _paper_ids(frame: pd.DataFrame) -> list[str]:
    return [str(value) for value in frame.get("paper_id", pd.Series(dtype="object")).tolist()]


def _rebuild_embedding_text(row: pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ]
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six deterministic corruption scenarios and write an audit log.

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
    corrupted = df.copy(deep=True).reset_index(drop=True)
    input_rows = len(corrupted)
    scenarios: list[dict[str, Any]] = []
    noise_by_id: dict[str, str] = {}

    if corrupted.empty:
        for name in (
            "drop_latest_records",
            "blank_summary",
            "inject_text_noise",
            "truncate_title",
            "stale_date",
            "duplicate_rows",
        ):
            scenarios.append({"scenario": name, "affected_rows": 0, "paper_ids": []})
        write_json(
            output_log_path,
            {
                "created_at": datetime.now(UTC).isoformat(),
                "input_rows": 0,
                "output_rows": 0,
                "scenarios": scenarios,
            },
        )
        return corrupted

    published = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    sorted_indices = published.sort_values(ascending=False, na_position="last").index
    drop_count = max(1, int(round(input_rows * 0.20)))
    dropped_indices = sorted_indices[:drop_count].tolist()
    corrupted = corrupted.drop(index=dropped_indices).reset_index(drop=True)
    scenarios.append(
        {
            "scenario": "drop_latest_records",
            "description": "Remove the most recently published records.",
            "affected_rows": len(dropped_indices),
            "paper_ids": [str(df.loc[index, "paper_id"]) for index in dropped_indices],
        }
    )

    blank_count = min(3, len(corrupted))
    blank_indices = corrupted.index[:blank_count]
    corrupted.loc[blank_indices, "summary"] = ""
    scenarios.append(
        {
            "scenario": "blank_summary",
            "description": "Clear summaries to simulate incomplete metadata.",
            "affected_rows": blank_count,
            "paper_ids": _paper_ids(corrupted.loc[blank_indices]),
        }
    )

    noise_count = min(3, len(corrupted))
    noise_indices = corrupted.index[-noise_count:]
    for position, index in enumerate(noise_indices, start=1):
        paper_id = str(corrupted.at[index, "paper_id"])
        noise_by_id[paper_id] = f" __CORRUPTION_NOISE_{position:02d}__ ###"
    scenarios.append(
        {
            "scenario": "inject_text_noise",
            "description": "Append meaningless tokens to text_for_embedding.",
            "affected_rows": noise_count,
            "paper_ids": _paper_ids(corrupted.loc[noise_indices]),
        }
    )

    title_count = min(3, len(corrupted))
    title_indices = corrupted.index[blank_count : blank_count + title_count]
    original_titles = {
        str(corrupted.at[index, "paper_id"]): str(corrupted.at[index, "title"])
        for index in title_indices
    }
    corrupted.loc[title_indices, "title"] = corrupted.loc[title_indices, "title"].astype(str).str[:7]
    scenarios.append(
        {
            "scenario": "truncate_title",
            "description": "Truncate titles to fewer than ten characters.",
            "affected_rows": title_count,
            "paper_ids": _paper_ids(corrupted.loc[title_indices]),
            "original_titles": original_titles,
        }
    )

    stale_count = min(7, len(corrupted))
    stale_indices = corrupted.index[:stale_count]
    stale_date = (pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=5)).date().isoformat()
    original_dates = {
        str(corrupted.at[index, "paper_id"]): str(corrupted.at[index, "published"])
        for index in stale_indices
    }
    corrupted.loc[stale_indices, "published"] = stale_date
    scenarios.append(
        {
            "scenario": "stale_date",
            "description": "Move publication dates five years into the past.",
            "affected_rows": stale_count,
            "paper_ids": _paper_ids(corrupted.loc[stale_indices]),
            "original_dates": original_dates,
            "replacement_date": stale_date,
        }
    )

    duplicate_count = min(drop_count, len(corrupted))
    duplicate_source = corrupted.head(duplicate_count).copy(deep=True)
    corrupted = pd.concat([corrupted, duplicate_source], ignore_index=True)
    scenarios.append(
        {
            "scenario": "duplicate_rows",
            "description": "Append duplicate copies of corrupted records.",
            "affected_rows": duplicate_count,
            "paper_ids": _paper_ids(duplicate_source),
        }
    )

    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    for index, row in corrupted.iterrows():
        base_text = _rebuild_embedding_text(row)
        corrupted.at[index, "text_for_embedding"] = base_text + noise_by_id.get(
            str(row["paper_id"]), ""
        )

    log = {
        "created_at": datetime.now(UTC).isoformat(),
        "input_rows": input_rows,
        "output_rows": len(corrupted),
        "scenarios": scenarios,
    }
    write_json(output_log_path, log)
    return corrupted.reset_index(drop=True)
