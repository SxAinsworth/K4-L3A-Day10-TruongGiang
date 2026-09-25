from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
import json
from pathlib import Path
import re
import time

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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref work-list payload into normalized paper records.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    def text(value: object) -> str:
        if isinstance(value, list):
            value = value[0] if value else ""
        return normalize_whitespace(unescape(str(value or "")))

    def clean_markup(value: object) -> str:
        # Crossref abstracts commonly contain JATS tags.  Removing every tag also
        # handles ordinary HTML without adding another parsing dependency.
        return normalize_whitespace(unescape(re.sub(r"<[^>]+>", " ", str(value or ""))))

    def doi(value: object) -> str:
        normalized = text(value).lower()
        normalized = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", normalized)
        return normalized.strip().rstrip(".,")

    def crossref_date(value: object) -> str:
        if isinstance(value, dict):
            raw = value.get("date-parts")
            if isinstance(raw, list) and raw and isinstance(raw[0], list) and raw[0]:
                parts = raw[0]
                try:
                    return date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1,
                                int(parts[2]) if len(parts) > 2 else 1).isoformat()
                except (TypeError, ValueError):
                    pass
            date_time = value.get("date-time")
            if date_time:
                return str(date_time)[:10]
        return ""

    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    records: list[PaperRecord] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        paper_id = doi(item.get("DOI"))
        title = text(item.get("title"))
        summary = clean_markup(item.get("abstract"))
        published = crossref_date(
            item.get("published") or item.get("published-print") or item.get("published-online")
        )
        if not paper_id or not title or not published:
            continue

        authors = []
        for author in item.get("author", []) or []:
            if isinstance(author, dict):
                name = text(f"{author.get('given', '')} {author.get('family', '')}")
                if name:
                    authors.append(name)
        categories = [text(subject) for subject in (item.get("subject", []) or []) if text(subject)]
        updated = crossref_date(item.get("updated") or item.get("indexed") or item.get("created")) or published
        abs_url = text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = abs_url
        for link in item.get("link", []) or []:
            if isinstance(link, dict) and (
                link.get("content-type") == "application/pdf" or link.get("content-version") == "vor"
            ):
                pdf_url = text(link.get("URL")) or pdf_url
                if link.get("content-type") == "application/pdf":
                    break

        records.append(PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "",
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=f"Crossref record {paper_id}",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records with retry, persistence, and offline fallback.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    endpoint = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    payload: dict | None = None
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            response = requests.get(
                endpoint,
                params=params,
                headers={"User-Agent": "day10-data-observability-lab/0.1"},
                timeout=20,
            )
            if response.status_code in {429, 503}:
                raise requests.HTTPError(f"Crossref returned HTTP {response.status_code}")
            response.raise_for_status()
            candidate = response.json()
            candidate_records = parse_crossref_payload(candidate)
            if len(candidate_records) < settings.max_results:
                raise ValueError(
                    f"Crossref returned only {len(candidate_records)} valid records; "
                    f"expected {settings.max_results}"
                )
            payload = candidate
            write_json(settings.paths.raw_api_response, payload)
            break
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)

    if payload is None:
        snapshot = settings.paths.raw_api_response
        if not snapshot.exists():
            raise RuntimeError("Crossref is unavailable and the offline snapshot is missing") from last_error
        payload = json.loads(snapshot.read_text(encoding="utf-8"))

    records = parse_crossref_payload(payload)[: settings.max_results]
    if not records:
        raise ValueError("No valid Crossref records were found in the API response or snapshot")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a normalized JSON snapshot into ``PaperRecord`` objects."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of records in {path}")
    records: list[PaperRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        values = dict(item)
        values["authors"] = list(values.get("authors") or [])
        values["categories"] = list(values.get("categories") or [])
        records.append(PaperRecord(**values))
    return records
