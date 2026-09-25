from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
import html
import json
from pathlib import Path
import re

import requests

from core.config import Settings
from core.utils import normalize_whitespace, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _normalize_doi(value: object) -> str:
    doi = normalize_whitespace(str(value or ""))
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi.rstrip(".,;)").lower()


def _clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def _iso_date(date_parts: object) -> str:
    if not isinstance(date_parts, list) or not date_parts:
        return ""
    try:
        parts = [int(part) for part in date_parts[:3]]
        if len(parts) == 1:
            return f"{parts[0]:04d}-01-01"
        if len(parts) == 2:
            return f"{parts[0]:04d}-{parts[1]:02d}-01"
        return datetime(*parts).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _crossref_date(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    date_parts = value.get("date-parts")
    if isinstance(date_parts, list) and date_parts:
        return _iso_date(date_parts[0])
    date_time = value.get("date-time")
    if not date_time:
        return ""
    try:
        return datetime.fromisoformat(str(date_time).replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _record_from_dict(item: dict) -> PaperRecord | None:
    paper_id = _normalize_doi(item.get("paper_id", item.get("DOI")))
    title_value = item.get("title", "")
    if isinstance(title_value, list):
        title_value = title_value[0] if title_value else ""
    title = _clean_text(title_value)
    if not paper_id or not title:
        return None

    authors: list[str] = []
    author_values = item.get("author", item.get("authors", [])) or []
    for author in author_values:
        if isinstance(author, str):
            name = _clean_text(author)
        else:
            name = _clean_text(
                " ".join(
                    part for part in (author.get("given", ""), author.get("family", "")) if part
                )
            )
            name = name or _clean_text(author.get("name", ""))
        if name:
            authors.append(name)

    categories = [
        _clean_text(category)
        for category in (item.get("subject", item.get("categories", [])) or [])
        if _clean_text(category)
    ]
    published = _crossref_date(item.get("published")) or _clean_text(item.get("published", ""))
    updated = (
        _crossref_date(item.get("updated"))
        or _crossref_date(item.get("created"))
        or published
    )
    abs_url = _clean_text(item.get("URL", item.get("abs_url", ""))) or f"https://doi.org/{paper_id}"
    pdf_url = _clean_text(item.get("pdf_url", "")) or abs_url

    return PaperRecord(
        paper_id=paper_id,
        title=title,
        summary=_clean_text(item.get("abstract", item.get("summary", ""))),
        authors=authors,
        categories=categories,
        primary_category=categories[0] if categories else "",
        published=published,
        updated=updated,
        abs_url=abs_url,
        pdf_url=pdf_url,
        comment=_clean_text(item.get("comment", "")) or f"Crossref record {paper_id}",
    )


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref response into normalized paper records.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    records: list[PaperRecord] = []
    for item in items:
        if isinstance(item, dict):
            record = _record_from_dict(item)
            if record is not None:
                records.append(record)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, falling back to the local snapshot when needed.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    snapshot_path = settings.paths.raw_api_response

    def load_snapshot() -> list[PaperRecord]:
        if not snapshot_path.exists():
            raise RuntimeError("Crossref unavailable and no local snapshot was found.")
        return parse_crossref_payload(json.loads(snapshot_path.read_text(encoding="utf-8")))

    if not settings.refresh_source and snapshot_path.exists():
        records = load_snapshot()
    else:
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params={
                    "query": settings.source_query,
                    "filter": settings.source_filter,
                    "rows": settings.max_results,
                },
                headers={"User-Agent": "day10-data-observability-lab/0.1"},
                timeout=20,
            )
            if response.status_code == 429:
                records = load_snapshot()
            else:
                response.raise_for_status()
                payload = response.json()
                snapshot_path.parent.mkdir(parents=True, exist_ok=True)
                snapshot_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
                )
                records = parse_crossref_payload(payload)
        except (requests.RequestException, ValueError, OSError):
            records = load_snapshot()

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load normalized records from ``crossref_records.json``."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return parse_crossref_payload(payload)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of records in {path}.")
    return [record for item in payload if isinstance(item, dict) if (record := _record_from_dict(item))]
