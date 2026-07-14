"""Persist deterministic exact and near-duplicate publication clusters."""

import uuid
from collections import defaultdict
from datetime import date
from typing import Any

import psycopg

from ..transform.dedup import compare_publications


def cluster_publications(database_url: str, snapshot_date: date, threshold: float = 0.92) -> int:
    """Cluster same-day publications and mark exactly one stable representative per cluster."""
    with psycopg.connect(database_url) as connection:
        with connection.cursor(row_factory=psycopg.rows.dict_row) as cursor:
            rows = cursor.execute(
                """
                SELECT publication.publication_id, publication.vacancy_id, vacancy.employer_id,
                       employer.name AS employer_name, vacancy.name_raw
                FROM core.publications AS publication
                JOIN core.vacancies AS vacancy ON vacancy.vacancy_id = publication.vacancy_id
                LEFT JOIN core.employers AS employer ON employer.employer_id = vacancy.employer_id
                WHERE publication.snapshot_date = %s AND publication.is_active
                ORDER BY publication.publication_id
                """,
                (snapshot_date,),
            ).fetchall()
            groups = _groups(rows, threshold)
            cursor.execute(
                """
                UPDATE core.publications
                SET duplicate_cluster_id = NULL, is_representative = true
                WHERE snapshot_date = %s
                """,
                (snapshot_date,),
            )
            for members in groups:
                cluster_key = ":".join(str(item["publication_id"]) for item in members)
                cluster_id = uuid.uuid5(uuid.NAMESPACE_URL, cluster_key)
                cursor.execute(
                    """
                    INSERT INTO core.duplicate_clusters (
                      cluster_id, method, threshold, algorithm_version
                    )
                    VALUES (%s, 'employer_title_similarity', %s, 'baseline-v1')
                    ON CONFLICT (cluster_id) DO NOTHING
                    """,
                    (cluster_id, threshold),
                )
                representative = members[0]["publication_id"]
                for member in members:
                    cursor.execute(
                        """
                        INSERT INTO core.duplicate_cluster_members (
                          cluster_id, publication_id, similarity, is_representative
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (cluster_id, publication_id) DO UPDATE SET
                          similarity = EXCLUDED.similarity,
                          is_representative = EXCLUDED.is_representative
                        """,
                        (
                            cluster_id,
                            member["publication_id"],
                            member["similarity"],
                            member["publication_id"] == representative,
                        ),
                    )
                    cursor.execute(
                        """
                        UPDATE core.publications
                        SET duplicate_cluster_id = %s, is_representative = %s
                        WHERE publication_id = %s
                        """,
                        (
                            cluster_id,
                            member["publication_id"] == representative,
                            member["publication_id"],
                        ),
                    )
        connection.commit()
    return len(groups)


def _groups(rows: list[dict[str, Any]], threshold: float) -> list[list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        employer = str(row.get("employer_id") or "")
        buckets[employer].append({**row, "similarity": 1.0})
    groups: list[list[dict[str, Any]]] = []
    for candidates in buckets.values():
        while candidates:
            seed = candidates.pop(0)
            group = [seed]
            remaining: list[dict[str, Any]] = []
            for candidate in candidates:
                decision = compare_publications(
                    {
                        "vacancy_id": None,
                        "employer_name": seed["employer_name"],
                        "name": seed["name_raw"],
                    },
                    {
                        "vacancy_id": None,
                        "employer_name": candidate["employer_name"],
                        "name": candidate["name_raw"],
                    },
                    threshold=threshold,
                )
                if decision.is_duplicate:
                    candidate["similarity"] = decision.similarity
                    group.append(candidate)
                else:
                    remaining.append(candidate)
            candidates = remaining
            if len(group) > 1:
                groups.append(group)
    return groups
