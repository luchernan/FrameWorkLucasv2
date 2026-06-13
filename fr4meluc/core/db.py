"""Capa de base de datos SQLite para Fr4meLuc Enterprise.

Un único archivo fr4meluc.db almacena:
  clients   → empresa / cliente auditado
  projects  → campaña o contrato de auditoría (un cliente tiene N proyectos)
  scans     → cada ejecución del framework contra un target
  findings  → hallazgo individual (puerto, vuln, subdominio…)
  assets    → IPs / dominios confirmados de un proyecto

La DB se crea en el directorio de trabajo actual (donde se lanza fr4meluc).
Llama init_db() en el arranque; es idempotente: CREATE TABLE IF NOT EXISTS.
"""

import sqlite3
import os
from datetime import datetime

DB_FILE = "fr4meluc.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # filas accesibles como dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Crea las tablas si no existen. Seguro de llamar múltiples veces."""
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            contact     TEXT,
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id   INTEGER NOT NULL REFERENCES clients(id),
            name        TEXT NOT NULL,
            scope       TEXT,
            status      TEXT DEFAULT 'active',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS scans (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id    INTEGER REFERENCES projects(id),
            target        TEXT NOT NULL,
            workspace_dir TEXT,
            profile       TEXT DEFAULT 'manual',
            status        TEXT DEFAULT 'running',
            started_at    TEXT DEFAULT (datetime('now')),
            finished_at   TEXT,
            notes         TEXT
        );

        CREATE TABLE IF NOT EXISTS findings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id     INTEGER NOT NULL REFERENCES scans(id),
            category    TEXT NOT NULL,
            title       TEXT NOT NULL,
            severity    TEXT DEFAULT 'info',
            detail      TEXT,
            evidence    TEXT,
            status      TEXT DEFAULT 'open',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS assets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL REFERENCES projects(id),
            value       TEXT NOT NULL,
            type        TEXT DEFAULT 'ip',
            notes       TEXT
        );

        CREATE TABLE IF NOT EXISTS scheduler_jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER REFERENCES projects(id),
            name        TEXT NOT NULL,
            targets     TEXT NOT NULL,
            profile     TEXT DEFAULT 'auto',
            cron_expr   TEXT NOT NULL,
            enabled     INTEGER DEFAULT 1,
            last_run    TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        """)
