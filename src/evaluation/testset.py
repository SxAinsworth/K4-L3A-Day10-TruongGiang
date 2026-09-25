from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


def _text(value: Any) -> str:
   return normalize_whitespace(str(value or ""))


def _authors(row: dict[str, Any]) -> str:
   joined = _text(row.get("authors_joined"))
   if joined:
      return joined
   authors = row.get("authors", []) or []
   return ", ".join(_text(author) for author in authors if _text(author))


def _categories(row: dict[str, Any]) -> str:
   joined = _text(row.get("categories_joined"))
   if joined:
      return joined
   categories = row.get("categories", []) or []
   return ", ".join(_text(category) for category in categories if _text(category))


def _make_item(item_id: str, question_type: str, question: str, ground_truth: str, doc_ids: list[str]) -> dict[str, Any]:
   return {
      "id": item_id,
      "type": question_type,
      "question_type": question_type,
      "question": question,
      "ground_truth": ground_truth,
      "ground_truth_doc_ids": doc_ids,
   }

def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
   """Build deterministic benchmark questions from cleaned paper metadata.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
   required_columns = {"paper_id", "title", "summary", "published"}
   missing_columns = required_columns.difference(df.columns)
   if missing_columns:
      raise ValueError(f"Clean dataframe is missing columns: {sorted(missing_columns)}")

   documents = []
   for row in df.to_dict(orient="records"):
      paper_id = _text(row.get("paper_id"))
      title = _text(row.get("title"))
      summary = _text(row.get("summary"))
      published = _text(row.get("published"))
      if paper_id and title and summary and published:
         row.update(
            {
               "paper_id": paper_id,
               "title": title,
               "summary": summary,
               "published": published,
            }
         )
         documents.append(row)

   if len(documents) < 2:
      raise ValueError("At least two valid papers are required to build the multi_hop benchmark.")

   samples: list[dict[str, Any]] = []
   for index, row in enumerate(documents[:2], start=1):
      paper_id = row["paper_id"]
      title = row["title"]
      samples.extend(
         [
            _make_item(
               f"eval_{len(samples) + 1:03d}",
               "summary",
               f"What is the main research summary of the paper '{title}'?",
               first_sentence(row["summary"]),
               [paper_id],
            ),
            _make_item(
               f"eval_{len(samples) + 1:03d}",
               "authors",
               f"Who authored the study '{title}'?",
               _authors(row),
               [paper_id],
            ),
            _make_item(
               f"eval_{len(samples) + 1:03d}",
               "date",
               f"When was the study '{title}' published?",
               row["published"],
               [paper_id],
            ),
            _make_item(
               f"eval_{len(samples) + 1:03d}",
               "category",
               f"What categories does the paper '{title}' belong to?",
               _categories(row),
               [paper_id],
            ),
         ]
      )

   first, second = documents[:2]
   first_categories = _categories(first) or "an unspecified field"
   second_categories = _categories(second) or "an unspecified field"
   multi_hop_ground_truth = (
      f"'{first['title']}' belongs to {first_categories} and studies "
      f"{first_sentence(first['summary'])} "
      f"'{second['title']}' belongs to {second_categories} and studies "
      f"{first_sentence(second['summary'])}"
   )
   samples = samples[:8]
   samples.extend(
      [
         _make_item(
            "eval_009",
            "multi_hop",
            f"How do the research areas of '{first['title']}' and '{second['title']}' connect?",
            multi_hop_ground_truth,
            [first["paper_id"], second["paper_id"]],
         ),
         _make_item(
            "eval_010",
            "multi_hop",
            f"Compare the publication dates and categories of '{first['title']}' and '{second['title']}'.",
            (
               f"'{first['title']}' was published on {first['published']} in {first_categories}; "
               f"'{second['title']}' was published on {second['published']} in {second_categories}."
            ),
            [first["paper_id"], second["paper_id"]],
         ),
      ]
   )
   write_json(output_path, samples)
   return samples
