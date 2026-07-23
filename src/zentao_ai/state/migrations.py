from __future__ import annotations

import sqlite3

MIGRATIONS = (
    """
CREATE TABLE leases (
 lease_id TEXT PRIMARY KEY, business_date TEXT NOT NULL, run_kind TEXT NOT NULL,
 owner TEXT NOT NULL, status TEXT NOT NULL, acquired_at TEXT NOT NULL,
 expires_at TEXT NOT NULL, released_at TEXT, previous_owner TEXT, active INTEGER NOT NULL
);
CREATE UNIQUE INDEX one_active_lease ON leases(business_date, run_kind) WHERE active=1;
CREATE TABLE comments (
 idempotency_key TEXT PRIMARY KEY, bug_id TEXT NOT NULL, payload_json TEXT NOT NULL,
 payload_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE core_outbox (
 idempotency_key TEXT PRIMARY KEY, run_kind TEXT NOT NULL, payload_json TEXT NOT NULL,
 payload_hash TEXT NOT NULL, status TEXT NOT NULL, external_id TEXT, created_at TEXT NOT NULL
);
CREATE TABLE core_checkpoints (
 business_date TEXT NOT NULL, run_kind TEXT NOT NULL, payload_json TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(business_date, run_kind)
);
CREATE TABLE job_leases (job_key TEXT PRIMARY KEY, owner TEXT NOT NULL, business_date TEXT NOT NULL, status TEXT NOT NULL, acquired_at TEXT NOT NULL, expires_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE bug_leases (job_key TEXT NOT NULL, bug_id TEXT NOT NULL, owner TEXT NOT NULL, expires_at TEXT NOT NULL, PRIMARY KEY(job_key, bug_id));
CREATE TABLE repo_leases (repo_key TEXT PRIMARY KEY, owner TEXT NOT NULL, expires_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE legacy_checkpoints (job_key TEXT NOT NULL, bug_id TEXT NOT NULL, snapshot_version TEXT NOT NULL, stage TEXT NOT NULL, payload_json TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(job_key, bug_id));
CREATE TABLE comment_records (idempotency_key TEXT PRIMARY KEY, bug_id TEXT NOT NULL, snapshot_version TEXT NOT NULL, decision TEXT NOT NULL, comment_id TEXT, status TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE legacy_outbox (outbox_key TEXT PRIMARY KEY, job_key TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, created_at TEXT NOT NULL, sent_at TEXT);
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
