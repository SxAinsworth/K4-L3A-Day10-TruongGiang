from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
   """Build a normalized, deduplicated dataframe ready for embedding.

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
   run_timestamp = pd.Timestamp(run_date)
   if run_timestamp.tzinfo is None:
      run_timestamp = run_timestamp.tz_localize("UTC")
   else:
      run_timestamp = run_timestamp.tz_convert("UTC")

   rows: list[dict] = []
   for record in records:
      row = asdict(record)
      paper_id = normalize_whitespace(row["paper_id"])
      title = normalize_whitespace(row["title"])
      summary = normalize_whitespace(row["summary"])
      authors = [normalize_whitespace(author) for author in row["authors"] if normalize_whitespace(author)]
      categories = [
         normalize_whitespace(category)
         for category in row["categories"]
         if normalize_whitespace(category)
      ]
      published_timestamp = pd.to_datetime(row["published"], errors="coerce", utc=True)
      if not paper_id or not title or pd.isna(published_timestamp):
         continue

      published = published_timestamp.date().isoformat()
      row.update(
         {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "primary_category": categories[0] if categories else "",
            "published": published,
            "updated": normalize_whitespace(row["updated"]),
            "authors_joined": ", ".join(authors),
            "categories_joined": ", ".join(categories),
            "summary_chars": len(summary),
            "age_days": (run_timestamp - published_timestamp).days,
         }
      )
      row["text_for_embedding"] = "\n".join(
         [
            f"Title: {title}",
            f"Authors: {row['authors_joined']}",
            f"Published: {published}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {summary}",
         ]
      )
      rows.append(row)

   columns = [
      "paper_id",
      "title",
      "summary",
      "authors",
      "categories",
      "primary_category",
      "published",
      "updated",
      "abs_url",
      "pdf_url",
      "comment",
      "authors_joined",
      "categories_joined",
      "summary_chars",
      "age_days",
      "text_for_embedding",
   ]
   dataframe = pd.DataFrame(rows, columns=columns)
   if dataframe.empty:
      return dataframe
   return (
      dataframe.drop_duplicates(subset="paper_id", keep="first")
      .sort_values("paper_id")
      .reset_index(drop=True)
   )
