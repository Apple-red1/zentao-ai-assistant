from __future__ import annotations

import sqlite3

MIGRATIONS = (
    """
CREATE TABLE leases (
 lease_id TEXT PRIMARY KEY, business_date TEXT NOT NULL, run_kind TEXT NOT NULL,
 owner TEXT NOT NULL, status TEXT NOT NULL, acquired_at TEXT NOT NULL,
 expires_at TEXT NOT NULL, released_at TEXT, previous_owner TEXT,
 UNIQUE(business_date, run_kind)
);
CREATE TABLE comments (
 idempotency_key TEXT PRIMARY KEY, bug_id TEXT NOT NULL, payload_json TEXT NOT NULL,
 payload_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE outbox (
 idempotency_key TEXT PRIMARY KEY, run_kind TEXT NOT NULL, payload_json TEXT NOT NULL,
 payload_hash TEXT NOT NULL, status TEXT NOT NULL, external_id TEXT, created_at TEXT NOT NULL
);
CREATE TABLE checkpoints (
 business_date TEXT NOT NULL, run_kind TEXT NOT NULL, payload_json TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(business_date, run_kind)
);
""",
)


def migrate(connection: sqlite3.Connection) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > len(MIGRATIONS):
        raise sqlite3.DatabaseError("database schema is newer than this application")
    for index in range(version, len(MIGRATIONS)):
        connection.execute("BEGIN IMMEDIATE")
        try:
            for statement in MIGRATIONS[index].split(";"):
                if statement.strip():
                    connection.execute(statement)
            connection.execute(f"PRAGMA user_version={index + 1}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
