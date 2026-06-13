"""Tests for fr4meluc.core.pipeline — run_cmd and save_finding are patched.

The pipeline module binds run_cmd and save_finding into its own namespace via
`from .runner import run_cmd` / `from .storage import save_finding`, so the
monkeypatch target is the import location in pipeline, not the source module.
"""
import pytest

from fr4meluc.core.pipeline import (
    _cond_web, _cond_smb, _cond_wordpress,
    run_pipeline, RULES,
)


# ─────────────────────────────────────────────────────────────
#  Condition helpers — pure, no patching
# ─────────────────────────────────────────────────────────────

def test_cond_web_port80():
    """An open port 80 satisfies the web condition."""
    ports = [{"port": "80", "state": "open", "service": "http", "version": ""}]
    assert _cond_web(ports) is True


def test_cond_web_service_name():
    """Web is detected by service name on a non-standard port (8080/http-proxy)."""
    ports = [{"port": "8080", "state": "open", "service": "http-proxy", "version": ""}]
    assert _cond_web(ports) is True


def test_cond_web_closed_port():
    """A closed port 80 does not satisfy the web condition."""
    ports = [{"port": "80", "state": "closed", "service": "http", "version": ""}]
    assert _cond_web(ports) is False


def test_cond_smb_port445():
    """An open port 445 satisfies the SMB condition."""
    ports = [{"port": "445", "state": "open", "service": "netbios-ssn", "version": ""}]
    assert _cond_smb(ports) is True


def test_cond_wordpress():
    """A WordPress version string satisfies the WordPress condition."""
    ports = [{"port": "80", "state": "open", "service": "http", "version": "WordPress 6.2"}]
    assert _cond_wordpress(ports) is True


# ─────────────────────────────────────────────────────────────
#  run_pipeline — subprocess + persistence fully patched
# ─────────────────────────────────────────────────────────────

def test_run_pipeline_web_rule_fires(tmp_path, monkeypatch):
    """An open web port fires only the web rule; SMB stays unrun."""
    monkeypatch.setattr("fr4meluc.core.pipeline.run_cmd", lambda *a, **kw: "")
    monkeypatch.setattr("fr4meluc.core.pipeline.save_finding", lambda *a, **kw: 1)

    ports = [{"port": "80", "state": "open", "service": "http", "version": ""}]
    ran = run_pipeline(ports, str(tmp_path), "10.0.0.1", 1)

    assert "web (gobuster+nuclei)" in ran
    assert "smb (enum4linux)" not in ran


def test_run_pipeline_empty_ports(tmp_path, monkeypatch):
    """No ports means no rule fires and nothing runs."""
    monkeypatch.setattr("fr4meluc.core.pipeline.run_cmd", lambda *a, **kw: "")
    monkeypatch.setattr("fr4meluc.core.pipeline.save_finding", lambda *a, **kw: 1)

    ran = run_pipeline([], str(tmp_path), "10.0.0.1", 1)

    assert ran == []


def test_rules_count():
    """The data-driven RULES list holds exactly three rules."""
    assert len(RULES) == 3
