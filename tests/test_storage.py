"""Tests for fr4meluc.core.storage — uses isolated SQLite DB via monkeypatch."""
import pytest

import fr4meluc.core.db as db_module
from fr4meluc.core.db import init_db, get_connection
from fr4meluc.core.storage import (
    get_or_create_client, get_or_create_project,
    create_scan, finish_scan, get_scan, save_finding, get_scan_findings,
    diff_scans, list_scheduler_jobs, update_job_last_run,
)


@pytest.fixture(scope="function")
def isolated_db(tmp_path, monkeypatch):
    """Point DB_FILE at a per-test tempfile, then init the schema.

    Every storage call (get_connection) reads db_module.DB_FILE fresh, so
    patching it before init_db() fully isolates each test. tmp_path is removed
    automatically by pytest, so no explicit cleanup is needed.
    """
    monkeypatch.setattr(db_module, "DB_FILE", str(tmp_path / "test.db"))
    init_db()
    yield


def test_create_and_get_scan(isolated_db, tmp_path, monkeypatch):
    """A created scan is retrievable with its target intact."""
    scan_id = create_scan("10.0.0.1", str(tmp_path), None, "test")
    scan = get_scan(scan_id)
    assert scan is not None
    assert scan["target"] == "10.0.0.1"


def test_finish_scan_sets_status(isolated_db, tmp_path, monkeypatch):
    """finish_scan flips status and stamps finished_at."""
    scan_id = create_scan("10.0.0.1", str(tmp_path), None, "test")
    finish_scan(scan_id, status="completed")
    scan = get_scan(scan_id)
    assert scan["status"] == "completed"
    assert scan["finished_at"] is not None


def test_save_and_get_findings(isolated_db, tmp_path, monkeypatch):
    """A saved finding comes back from get_scan_findings with its title."""
    scan_id = create_scan("10.0.0.1", str(tmp_path), None, "test")
    save_finding(scan_id, "nuclei", "SQL Injection", "critical", "detail", "evidence")
    findings = get_scan_findings(scan_id)
    assert len(findings) == 1
    assert findings[0]["title"] == "SQL Injection"


def test_diff_scans(isolated_db, tmp_path, monkeypatch):
    """diff_scans classifies findings as new / resolved / persisted by title."""
    scan_a = create_scan("10.0.0.1", str(tmp_path), None, "test")
    save_finding(scan_a, "web", "Open Port 80", "info")
    save_finding(scan_a, "nuclei", "XSS", "high")

    scan_b = create_scan("10.0.0.1", str(tmp_path), None, "test")
    save_finding(scan_b, "nuclei", "XSS", "high")
    save_finding(scan_b, "nuclei", "SQLi", "critical")

    diff = diff_scans(scan_a, scan_b)

    new_titles = sorted(f["title"] for f in diff["new"])
    resolved_titles = sorted(f["title"] for f in diff["resolved"])
    persisted_titles = sorted(f["title"] for f in diff["persisted"])

    assert new_titles == ["SQLi"]
    assert resolved_titles == ["Open Port 80"]
    assert persisted_titles == ["XSS"]


def test_list_scheduler_jobs_enabled_filter(isolated_db, tmp_path, monkeypatch):
    """enabled_only filters to enabled=1; False returns every job."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO scheduler_jobs (name, targets, cron_expr, enabled) "
            "VALUES (?, ?, ?, ?)",
            ("enabled-job", "10.0.0.1", "0 0 * * *", 1),
        )
        conn.execute(
            "INSERT INTO scheduler_jobs (name, targets, cron_expr, enabled) "
            "VALUES (?, ?, ?, ?)",
            ("disabled-job", "10.0.0.2", "0 0 * * *", 0),
        )

    enabled = list_scheduler_jobs(enabled_only=True)
    assert len(enabled) == 1
    assert enabled[0]["name"] == "enabled-job"

    all_jobs = list_scheduler_jobs(enabled_only=False)
    assert len(all_jobs) == 2


def test_update_job_last_run(isolated_db, tmp_path, monkeypatch):
    """update_job_last_run stamps last_run on the target job."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO scheduler_jobs (name, targets, cron_expr, enabled) "
            "VALUES (?, ?, ?, ?)",
            ("job-1", "10.0.0.1", "0 0 * * *", 1),
        )
        job_id = cur.lastrowid

    update_job_last_run(job_id)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT last_run FROM scheduler_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    assert row is not None
    assert row["last_run"] is not None
