"""Idempotent raw and core loaders with source provenance."""

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import psycopg

from ..transform.salary import normalize_salary
from ..transform.vacancy import canonicalize_vacancy


def load_raw_snapshot(
    database_url: str, raw_root: Path, snapshot_date: date, run_id: uuid.UUID
) -> dict[str, int]:
    """Load accepted raw page files, preserving a deterministic provenance graph."""
    pages = sorted((raw_root / snapshot_date.isoformat()).rglob("page-*.json"))
    snapshot_at = datetime.combine(snapshot_date, datetime.min.time(), tzinfo=timezone.utc)
    loaded_pages = loaded_vacancies = 0
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ops.pipeline_runs (
                  run_id, pipeline_name, snapshot_date, status, code_version, config_hash
                )
                VALUES (%s, 'load', %s, 'started', '0.1.0', 'local')
                ON CONFLICT (run_id) DO NOTHING
                """,
                (run_id, snapshot_date),
            )
            for path in pages:
                payload = json.loads(path.read_text(encoding="utf-8"))
                query_id, area_id, page_no = _page_identity(raw_root, snapshot_date, path)
                request_id = uuid.uuid5(run_id, f"{query_id}:{area_id}:{page_no}")
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                items = payload.get("items", [])
                if not isinstance(items, list):
                    raise ValueError(f"Raw page has invalid items field: {path}")
                cursor.execute(
                    """
                    INSERT INTO raw.api_requests (
                      request_id, run_id, query_id, area_id, page_no, request_params, requested_at,
                      received_at, items_count, found_count, raw_path, sha256, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'succeeded')
                    ON CONFLICT (run_id, query_id, area_id, page_no) DO UPDATE SET
                      raw_path = EXCLUDED.raw_path, sha256 = EXCLUDED.sha256,
                      items_count = EXCLUDED.items_count, found_count = EXCLUDED.found_count
                    """,
                    (
                        request_id,
                        run_id,
                        query_id,
                        area_id,
                        page_no,
                        json.dumps({"source": "raw-file"}),
                        snapshot_at,
                        snapshot_at,
                        len(items),
                        payload.get("found"),
                        str(path.relative_to(raw_root)),
                        digest,
                    ),
                )
                for item in items:
                    if not isinstance(item, dict) or item.get("id") is None:
                        continue
                    item_digest = hashlib.sha256(
                        json.dumps(item, ensure_ascii=False, sort_keys=True).encode()
                    ).hexdigest()
                    cursor.execute(
                        """
                        INSERT INTO raw.vacancy_snapshots (
                          run_id, vacancy_id, snapshot_at, payload, payload_hash, source_request_id
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (vacancy_id, snapshot_at, payload_hash) DO NOTHING
                        """,
                        (
                            run_id,
                            str(item["id"]),
                            snapshot_at,
                            json.dumps(item),
                            item_digest,
                            request_id,
                        ),
                    )
                    loaded_vacancies += cursor.rowcount
                loaded_pages += 1
            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET status = 'succeeded', finished_at = now()
                WHERE run_id = %s
                """,
                (run_id,),
            )
        connection.commit()
    return {"pages": loaded_pages, "vacancy_snapshots": loaded_vacancies}


def load_core_snapshot(database_url: str, snapshot_date: date, run_id: uuid.UUID) -> dict[str, int]:
    """Upsert canonical vacancies and per-day publication history from raw snapshots."""
    vacancies = publications = 0
    with psycopg.connect(database_url) as connection:
        with connection.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            rows = cursor.execute(
                """
                SELECT snapshot_id, payload FROM raw.vacancy_snapshots
                WHERE run_id = %s ORDER BY snapshot_id
                """,
                (run_id,),
            ).fetchall()
            for row in rows:
                canonical = canonicalize_vacancy(row["payload"])
                now = datetime.now(timezone.utc)
                if canonical.employer_id:
                    cursor.execute(
                        """
                        INSERT INTO core.employers (
                          employer_id, name, normalized_name, first_seen_at, last_seen_at
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (employer_id) DO UPDATE SET
                          name = EXCLUDED.name, normalized_name = EXCLUDED.normalized_name,
                          last_seen_at = EXCLUDED.last_seen_at
                        """,
                        (
                            canonical.employer_id,
                            canonical.employer_name,
                            (canonical.employer_name or "").casefold(),
                            now,
                            now,
                        ),
                    )
                cursor.execute(
                    """
                    INSERT INTO core.vacancies (
                      vacancy_id, employer_id, name_raw, name_normalized, description_html,
                      description_text, area_id, area_name, published_at, alternate_url,
                      first_seen_at, last_seen_at, content_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (vacancy_id) DO UPDATE SET
                      employer_id = EXCLUDED.employer_id, name_raw = EXCLUDED.name_raw,
                      name_normalized = EXCLUDED.name_normalized,
                      description_html = EXCLUDED.description_html,
                      description_text = EXCLUDED.description_text, area_id = EXCLUDED.area_id,
                      area_name = EXCLUDED.area_name, published_at = EXCLUDED.published_at,
                      alternate_url = EXCLUDED.alternate_url, last_seen_at = EXCLUDED.last_seen_at,
                      content_hash = EXCLUDED.content_hash
                    """,
                    (
                        canonical.vacancy_id,
                        canonical.employer_id,
                        canonical.name_raw,
                        canonical.name_normalized,
                        canonical.description_html,
                        canonical.description_text,
                        canonical.area_id,
                        canonical.area_name,
                        canonical.published_at,
                        canonical.alternate_url,
                        now,
                        now,
                        canonical.content_hash,
                    ),
                )
                salary = row["payload"].get("salary")
                if isinstance(salary, dict):
                    raw_from = salary.get("from")
                    raw_to = salary.get("to")
                    currency = salary.get("currency")
                    result = normalize_salary(raw_from, raw_to, currency)
                    cursor.execute(
                        """
                        INSERT INTO core.salary_offers (
                          vacancy_id, from_raw, to_raw, currency_raw, gross_raw,
                          from_rub, to_rub, midpoint_rub, is_gross, normalization_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (vacancy_id) DO UPDATE SET
                          from_raw = EXCLUDED.from_raw, to_raw = EXCLUDED.to_raw,
                          currency_raw = EXCLUDED.currency_raw, gross_raw = EXCLUDED.gross_raw,
                          from_rub = EXCLUDED.from_rub, to_rub = EXCLUDED.to_rub,
                          midpoint_rub = EXCLUDED.midpoint_rub, is_gross = EXCLUDED.is_gross,
                          normalization_status = EXCLUDED.normalization_status
                        """,
                        (
                            canonical.vacancy_id,
                            raw_from,
                            raw_to,
                            currency,
                            salary.get("gross"),
                            result.from_rub,
                            result.to_rub,
                            result.midpoint_rub,
                            salary.get("gross"),
                            result.status,
                        ),
                    )
                cursor.execute(
                    """
                    INSERT INTO core.publications (
                      vacancy_id, snapshot_date, published_at, content_hash, is_active,
                      source_snapshot_id, is_representative
                    ) VALUES (%s, %s, %s, %s, true, %s, true)
                    ON CONFLICT (vacancy_id, snapshot_date) DO UPDATE SET
                      content_hash = EXCLUDED.content_hash, is_active = true,
                      source_snapshot_id = EXCLUDED.source_snapshot_id, is_representative = true
                    """,
                    (
                        canonical.vacancy_id,
                        snapshot_date,
                        canonical.published_at,
                        canonical.content_hash,
                        row["snapshot_id"],
                    ),
                )
                vacancies += 1
                publications += 1
        connection.commit()
    return {"vacancies": vacancies, "publications": publications}


def _page_identity(raw_root: Path, snapshot_date: date, path: Path) -> tuple[str, int, int]:
    relative = path.relative_to(raw_root / snapshot_date.isoformat())
    page_no = int(path.stem.removeprefix("page-"))
    return relative.parts[0], int(relative.parts[1]), page_no
