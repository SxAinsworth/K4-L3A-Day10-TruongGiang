from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, read_json, write_json


class BenchmarkTestSet(list[dict[str, Any]]):
    """List-compatible benchmark result with the checkpoint's ``samples`` API."""

    @property
    def samples(self) -> "BenchmarkTestSet":
        return self


def _as_text(value: Any) -> str:
    """Convert a dataframe value to stable, human-readable benchmark text."""
    if isinstance(value, (list, tuple)):
        return ", ".join(normalize_whitespace(str(item)) for item in value if str(item).strip())
    return normalize_whitespace(str(value)) if pd.notna(value) else ""


def _published_label(value: Any) -> str:
    published = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(published):
        return "Unknown"
    return published.strftime("%B %Y")


def _category_label(value: Any) -> str:
    return _as_text(value) or "Crossref did not supply a specialist category."


def _sample(sample_id: int, question_type: str, question: str, ground_truth: str,
            doc_ids: list[str]) -> dict[str, Any]:
    return {
        "id": f"eval_{sample_id:03d}",
        "type": question_type,
        # The evaluator in this starter repo uses question_type.  Keeping both
        # fields preserves compatibility while exposing the requested schema.
        "question_type": question_type,
        "question": question,
        "ground_truth": ground_truth,
        "ground_truth_doc_ids": doc_ids,
    }


def build_test_set(df: pd.DataFrame, output_path) -> BenchmarkTestSet:
    """Build a deterministic, source-grounded benchmark from clean papers.

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
    required = {
        "paper_id", "title", "summary", "published", "authors_joined", "categories_joined"
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Cannot build test set; missing columns: {', '.join(missing)}")

    usable = df.copy()
    usable = usable.dropna(subset=["paper_id", "title", "summary"])
    usable = usable[
        usable["paper_id"].astype(str).str.strip().ne("")
        & usable["title"].astype(str).str.strip().ne("")
        & usable["summary"].astype(str).str.strip().ne("")
    ]
    usable = usable.drop_duplicates(subset=["paper_id"]).reset_index(drop=True)
    if len(usable) < 5:
        raise ValueError("At least 5 valid, unique papers are required to build the benchmark")

    # Deterministic spread across the corpus rather than relying on random state.
    positions = [round(index * (len(usable) - 1) / 9) for index in range(10)]
    papers = [usable.iloc[position] for position in positions]
    samples: list[dict[str, Any]] = []

    for row in papers[0:2]:
        title, paper_id = _as_text(row["title"]), _as_text(row["paper_id"])
        samples.append(_sample(
            len(samples) + 1,
            "summary",
            f'What is the main research contribution of "{title}"?',
            first_sentence(_as_text(row["summary"])),
            [paper_id],
        ))

    for row in papers[2:4]:
        title, paper_id = _as_text(row["title"]), _as_text(row["paper_id"])
        category = _category_label(row["categories_joined"])
        samples.append(_sample(
            len(samples) + 1,
            "authors",
            f'Who authored the research "{title}" about {category}?',
            _as_text(row["authors_joined"]),
            [paper_id],
        ))

    for row in papers[4:6]:
        title, paper_id = _as_text(row["title"]), _as_text(row["paper_id"])
        samples.append(_sample(
            len(samples) + 1,
            "date",
            f'In which month and year was "{title}" published?',
            _published_label(row["published"]),
            [paper_id],
        ))

    for row in papers[6:8]:
        title, paper_id = _as_text(row["title"]), _as_text(row["paper_id"])
        samples.append(_sample(
            len(samples) + 1,
            "category",
            f'Which specialist fields does the paper "{title}" belong to?',
            _category_label(row["categories_joined"]),
            [paper_id],
        ))

    for left, right in ((papers[8], papers[1]), (papers[9], papers[0])):
        left_title, right_title = _as_text(left["title"]), _as_text(right["title"])
        left_id, right_id = _as_text(left["paper_id"]), _as_text(right["paper_id"])
        left_category = _category_label(left["categories_joined"])
        right_category = _category_label(right["categories_joined"])
        ground_truth = (
            f'{left_title} ({left_category}): {first_sentence(_as_text(left["summary"]))} '
            f'{right_title} ({right_category}): {first_sentence(_as_text(right["summary"]))}'
        )
        samples.append(_sample(
            len(samples) + 1,
            "multi_hop",
            f'How do "{left_title}" and "{right_title}" complement each other across their fields?',
            ground_truth,
            [left_id, right_id],
        ))

    result = BenchmarkTestSet(samples)
    write_json(Path(output_path), result)
    return result


def load_or_create_test_set(df: pd.DataFrame, settings_or_path, refresh: bool | None = None) -> BenchmarkTestSet:
    """Load a stable benchmark unless it is missing or an explicit refresh is requested.

    ``settings_or_path`` accepts either the project Settings object or a direct
    output path, making the helper convenient in scripts and checkpoint commands.
    """
    if hasattr(settings_or_path, "paths"):
        output_path = Path(settings_or_path.paths.eval_testset)
        should_refresh = settings_or_path.refresh_test_set if refresh is None else refresh
    else:
        output_path = Path(settings_or_path)
        should_refresh = False if refresh is None else refresh

    if output_path.exists() and not should_refresh:
        payload = read_json(output_path)
        if isinstance(payload, list) and payload:
            return BenchmarkTestSet(payload)
    return build_test_set(df, output_path)
