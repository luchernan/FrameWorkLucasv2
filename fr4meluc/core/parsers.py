"""Parsers de salidas estructuradas (Nmap XML, Nuclei JSONL, FFuF JSON)."""
import os
import re
import json
import xml.etree.ElementTree as ET


def extract_domains_from_nmap(nmap_output: str) -> list:
    """Heurística para encontrar dominios mencionados en la salida de Nmap (-sC -sV)."""
    domains = set()
    redirects = re.findall(r'Did not follow redirect to https?://([^/:\s]+)', nmap_output)
    domains.update(redirects)
    ssl_names = re.findall(r'DNS:([^,\s]+)', nmap_output)
    domains.update(ssl_names)
    valid = [d for d in domains
             if d != 'localhost' and not re.match(r'^\d{1,3}(\.\d{1,3}){3}$', d)]
    return valid


def parse_nmap(nmap_file: str) -> list:
    """Parsea el XML de Nmap y devuelve lista de dicts con info de puertos."""
    ports = []
    if not os.path.exists(nmap_file):
        return ports
    try:
        tree = ET.parse(nmap_file)
        root = tree.getroot()
        for host in root.findall('host'):
            for port in host.findall('ports/port'):
                portid = port.get('portid')
                protocol = port.get('protocol')
                state = port.find('state').get('state')
                service = port.find('service')
                service_name = service.get('name') if service is not None else "unknown"
                product = service.get('product') if service is not None else ""
                version = service.get('version') if service is not None else ""
                ports.append({
                    'port': portid,
                    'protocol': protocol,
                    'state': state,
                    'service': service_name,
                    'version': f"{product} {version}".strip(),
                })
    except Exception:
        pass
    return ports


def parse_nuclei(report_dir: str) -> list:
    """Parsea nuclei.json (JSONL) y devuelve hallazgos normalizados."""
    nuclei_vulns = []
    nuclei_file = os.path.join(report_dir, "web", "nuclei.json")
    if not os.path.exists(nuclei_file):
        return nuclei_vulns
    try:
        with open(nuclei_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    vuln = json.loads(line)
                    nuclei_vulns.append({
                        'template-id': vuln.get('template-id'),
                        'name': vuln.get('info', {}).get('name'),
                        'severity': vuln.get('info', {}).get('severity', 'info'),
                        'type': vuln.get('type'),
                        'matched-at': vuln.get('matched-at'),
                    })
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return nuclei_vulns


def parse_ffuf(report_dir: str, domain: str) -> list:
    """Parsea el JSON de FFuF con resultados de subdominios."""
    results = []
    if not domain:
        return results
    json_file = os.path.join(report_dir, "web", f"ffuf_{domain.replace('.', '_')}.json")
    if not os.path.exists(json_file):
        return results
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for res in data.get('results', []):
                results.append({
                    'url': res.get('url'),
                    'status': res.get('status'),
                    'length': res.get('length'),
                    'input': res.get('input', {}).get('FUZZ'),
                })
    except Exception:
        pass
    return results
