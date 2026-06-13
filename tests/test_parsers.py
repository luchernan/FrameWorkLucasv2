"""Tests for fr4meluc.core.parsers — pure functions, no mocking needed."""
import os
import textwrap
import pytest

from fr4meluc.core.parsers import (
    extract_domains_from_nmap,
    parse_nmap,
    parse_nuclei,
)


# ─────────────────────────────────────────────────────────────
#  extract_domains_from_nmap
# ─────────────────────────────────────────────────────────────

def test_extract_domains_valid():
    """A DNS:<domain> entry surfaces the domain in the result list."""
    nmap_output = "ssl-cert: Subject Alternative Name: DNS:example.htb"
    domains = extract_domains_from_nmap(nmap_output)
    assert "example.htb" in domains


def test_extract_domains_filters_localhost():
    """'localhost' is explicitly filtered out of extracted domains."""
    nmap_output = "Subject Alternative Name: DNS:localhost, DNS:example.htb"
    domains = extract_domains_from_nmap(nmap_output)
    assert "localhost" not in domains
    assert "example.htb" in domains


def test_extract_domains_filters_ip():
    """A bare IPv4 in a DNS: entry is filtered (not a domain)."""
    nmap_output = "Subject Alternative Name: DNS:192.168.1.1, DNS:example.htb"
    domains = extract_domains_from_nmap(nmap_output)
    assert "192.168.1.1" not in domains
    assert "example.htb" in domains


def test_extract_domains_redirect():
    """A 'Did not follow redirect' line yields the redirect host."""
    nmap_output = "|_http-title: Did not follow redirect to https://target.htb/"
    domains = extract_domains_from_nmap(nmap_output)
    assert "target.htb" in domains


# ─────────────────────────────────────────────────────────────
#  parse_nmap
# ─────────────────────────────────────────────────────────────

_MINIMAL_NMAP_XML = textwrap.dedent(
    """\
    <?xml version="1.0"?>
    <nmaprun>
      <host>
        <ports>
          <port protocol="tcp" portid="80">
            <state state="open"/>
            <service name="http" product="Apache" version="2.4"/>
          </port>
        </ports>
      </host>
    </nmaprun>
    """
)


def test_parse_nmap_valid(tmp_path):
    """A valid nmap XML parses into at least one port dict with the core keys."""
    xml_file = tmp_path / "nmap.xml"
    xml_file.write_text(_MINIMAL_NMAP_XML, encoding="utf-8")

    ports = parse_nmap(str(xml_file))

    assert isinstance(ports, list)
    assert len(ports) >= 1
    first = ports[0]
    assert "port" in first
    assert "service" in first
    assert "state" in first
    assert first["port"] == "80"
    assert first["service"] == "http"
    assert first["state"] == "open"


def test_parse_nmap_missing_file():
    """A nonexistent path returns [] without raising."""
    assert parse_nmap("/nonexistent/path/nmap.xml") == []


# ─────────────────────────────────────────────────────────────
#  parse_nuclei
# ─────────────────────────────────────────────────────────────

def test_parse_nuclei_mixed_lines(tmp_path):
    """parse_nuclei skips invalid JSON lines and parses valid ones.

    parse_nuclei(report_dir) reads {report_dir}/web/nuclei.json, so the file is
    created under tmp_path/web/nuclei.json and tmp_path is passed as report_dir.
    """
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    nuclei_file = web_dir / "nuclei.json"
    nuclei_file.write_text(
        '{"template-id":"test-1","info":{"name":"Test Finding","severity":"high"},'
        '"matched-at":"http://10.0.0.1/test"}\n'
        "{broken}\n",
        encoding="utf-8",
    )

    result = parse_nuclei(str(tmp_path))

    assert len(result) == 1
    assert result[0]["severity"] == "high"
