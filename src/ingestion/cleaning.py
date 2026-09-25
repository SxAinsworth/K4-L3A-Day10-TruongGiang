from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a deduplicated, embedding-ready dataframe.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    columns = [
        "paper_id", "title", "summary", "authors", "categories", "primary_category",
        "published", "updated", "abs_url", "pdf_url", "comment", "authors_joined",
        "categories_joined", "summary_chars", "age_days", "text_for_embedding",
    ]
    rows = []
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")

    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = [normalize_whitespace(value) for value in record.authors if normalize_whitespace(value)]
        categories = [normalize_whitespace(value) for value in record.categories if normalize_whitespace(value)]
        published = pd.to_datetime(record.published, utc=True, errors="coerce")
        updated = pd.to_datetime(record.updated, utc=True, errors="coerce")
        if not paper_id or not title or pd.isna(published):
            continue

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        published_iso = published.date().isoformat()
        text_for_embedding = "\n".join([
            f"Title: {title}",
            f"Authors: {authors_joined}",
            f"Published: {published_iso}",
            f"Categories: {categories_joined}",
            f"Summary: {summary}",
        ])
        rows.append({
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "primary_category": normalize_whitespace(record.primary_category),
            "published": published,
            "updated": updated if not pd.isna(updated) else published,
            "abs_url": normalize_whitespace(record.abs_url),
            "pdf_url": normalize_whitespace(record.pdf_url),
            "comment": normalize_whitespace(record.comment),
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary),
            "age_days": (run_timestamp.date() - published.date()).days,
            "text_for_embedding": text_for_embedding,
        })

    if not rows:
        return pd.DataFrame(columns=columns)
    return (
        pd.DataFrame(rows, columns=columns)
        .drop_duplicates(subset=["paper_id"], keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
