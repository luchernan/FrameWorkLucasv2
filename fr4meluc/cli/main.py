"""Entry point CLI — orquesta los menús interactivos consumiendo core/.

Soporta:
  fr4meluc           → modo interactivo clásico
  fr4meluc --quiet   → silencia la capa educativa (uso pro)
"""
import sys
import time
import argparse
from colorama import init, Fore, Style

from ..core.ui import (
    _clr, _line, _box_title, _section, _opt, _prompt, _ok, _warn, _err, _info,
    _badge, print_banner, set_educational, W,
)
from ..core.validation import validate_target, check_dependencies
from ..core.workspace import create_workspace
from ..core.network import detect_os
from ..core.tools.nmap import run_nmap
from ..core.tools.arp_scan import do_arp_scan
from ..core.tools.gobuster import run_web_enum
from ..core.tools.ffuf import run_ffuf_subdomains
from ..core.tools.nuclei import run_nuclei
from ..core.tools.nikto import run_nikto
from ..core.tools.wpscan import run_wpscan
from ..core.tools.sqlmap import run_sqlmap
from ..core.tools.hydra import run_hydra_bruteforce
from ..core.tools.enum4linux import run_enum4linux
from ..core.tools.searchsploit import run_searchsploit
from ..core.tools.john import run_hash_cracking
from ..core.tools.peas import download_peas
from ..core.tools.http_server import start_http_server_payloads
from ..core.tools.netcat import run_netcat_listener
from ..core.report import generate_html_report
from ..core.report_pdf import generate_pdf_report
from ..core.report_docx import generate_docx_report
from ..core.db import init_db
from ..core.storage import (
    get_or_create_client, get_or_create_project,
    create_scan, finish_scan, save_finding,
    get_project_scans, diff_scans, import_workspace,
    get_scan,
)


# ─────────────────────────────────────────────────────────────
#  Sesión activa (project + scan en curso)
# ─────────────────────────────────────────────────────────────
_active_project_id: int | None = None
_active_scan_id: int | None = None


def _get_or_prompt_project() -> int | None:
    """Si no hay proyecto activo, pregunta cliente/proyecto al usuario."""
    global _active_project_id
    if _active_project_id is not None:
        return _active_project_id

    print(f"\n{Fore.CYAN}[DB] Para guardar esta sesión en el historial, introduce datos del cliente.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}[DB] (Enter para omitir y usar modo anónimo){Style.RESET_ALL}")
    client_name = input(f"  Nombre del cliente/empresa: ").strip()
    if not client_name:
        return None

    project_name = input(f"  Nombre del proyecto/auditoría: ").strip() or "Auditoría sin nombre"
    scope = input(f"  Scope (IPs/rangos/dominos, opcional): ").strip()

    client_id = get_or_create_client(client_name)
    project_id = get_or_create_project(client_id, project_name, scope)
    _active_project_id = project_id
    _ok(f"Proyecto '{project_name}' (cliente: {client_name}) activo. ID={project_id}")
    return project_id


def _show_history_and_diff(project_id: int) -> None:
    """Muestra histórico de escaneos del proyecto y permite hacer diff entre dos."""
    scans = get_project_scans(project_id)
    if not scans:
        _info("No hay escaneos previos registrados para este proyecto.")
        return

    print(f"\n{Fore.CYAN}╔{'═' * 70}╗")
    print(f"{Fore.CYAN}║{'  HISTÓRICO DE ESCANEOS':^70}║")
    print(f"{Fore.CYAN}╚{'═' * 70}╝{Style.RESET_ALL}")
    print(f"  {'ID':<5} {'TARGET':<20} {'ESTADO':<12} {'FECHA':<20} {'PERFIL'}")
    print(f"  {'-'*5} {'-'*20} {'-'*12} {'-'*20} {'-'*10}")
    for s in scans:
        sc = Fore.GREEN if s['status'] == 'completed' else Fore.YELLOW
        print(f"  {Fore.CYAN}{s['id']:<5}{Style.RESET_ALL} {s['target']:<20} "
              f"{sc}{s['status']:<12}{Style.RESET_ALL} {s['started_at']:<20} {s['profile']}")

    if len(scans) < 2:
        _info("Necesitas al menos 2 escaneos para hacer un diff.")
        return

    print()
    id_a = input(f"  {Fore.CYAN}ID del escaneo BASE (más antiguo): {Style.RESET_ALL}").strip()
    id_b = input(f"  {Fore.CYAN}ID del escaneo NUEVO (más reciente): {Style.RESET_ALL}").strip()

    if not id_a.isdigit() or not id_b.isdigit():
        _err("IDs deben ser números.")
        return

    diff = diff_scans(int(id_a), int(id_b))

    print(f"\n{Fore.CYAN}{'─'*72}")
    print(f"  DIFF  Escaneo #{id_a}  →  #{id_b}")
    print(f"{'─'*72}{Style.RESET_ALL}")

    if diff['new']:
        print(f"\n  {Fore.RED}✘  NUEVOS hallazgos ({len(diff['new'])}) — aparecieron en #{id_b}:{Style.RESET_ALL}")
        for f in diff['new']:
            sev_c = Fore.RED if f['severity'] in ('critical','high') else Fore.YELLOW
            print(f"    {sev_c}[{f['severity'].upper():<8}]{Style.RESET_ALL}  {f['category']:<12}  {f['title']}")

    if diff['resolved']:
        print(f"\n  {Fore.GREEN}✔  RESUELTOS ({len(diff['resolved'])}) — desaparecieron desde #{id_a}:{Style.RESET_ALL}")
        for f in diff['resolved']:
            print(f"    {Fore.GREEN}[{f['severity'].upper():<8}]{Style.RESET_ALL}  {f['category']:<12}  {f['title']}")

    if diff['persisted']:
        print(f"\n  {Fore.YELLOW}⚠  PERSISTENTES ({len(diff['persisted'])}) — presentes en ambos escaneos:{Style.RESET_ALL}")
        for f in diff['persisted']:
            print(f"    [{f['severity'].upper():<8}]  {f['category']:<12}  {f['title']}")

    if not diff['new'] and not diff['resolved']:
        _ok("Sin diferencias — los hallazgos son idénticos entre ambos escaneos.")


def _persist_nmap(scan_id: int, workspace_dir: str) -> None:
    """Lee nmap.xml del workspace y guarda los puertos abiertos como findings."""
    import os
    from ..core.parsers import parse_nmap
    nmap_xml = os.path.join(workspace_dir, "nmap", "nmap.xml")
    for port in parse_nmap(nmap_xml):
        if port["state"] == "open":
            save_finding(
                scan_id,
                category="port",
                title=f"{port['port']}/{port['protocol']} {port['service']}",
                severity="info",
                detail=port.get("version", ""),
            )


def _persist_nuclei(scan_id: int, workspace_dir: str) -> None:
    """Lee nuclei.json y guarda los hallazgos en la DB."""
    from ..core.parsers import parse_nuclei
    for vuln in parse_nuclei(workspace_dir):
        save_finding(
            scan_id,
            category="nuclei",
            title=vuln.get("name") or vuln.get("template-id", "?"),
            severity=vuln.get("severity", "info"),
            detail=vuln.get("matched-at", ""),
        )


def target_menu(ip):
    """Menú secundario encapsulado para concentrarse en un target particular."""
    global _active_scan_id

    workspace_dir = create_workspace(ip)
    if workspace_dir is None:
        return

    # Crear registro de escaneo en DB
    project_id = _get_or_prompt_project()
    scan_id = create_scan(ip, workspace_dir, project_id=project_id)
    _active_scan_id = scan_id

    active_target = ip
    active_domain = None
    has_web_flags = False
    active_protocol = "http://"
    nmap_executed = False

    while True:
        _clr()
        target_display = f"{ip}" if not active_domain else f"{ip}  ╱  {active_domain}"

        print(f"{Fore.GREEN}╔{'═' * (W-2)}╗")
        title_label = f"  PANEL DE ATAQUE  --  {target_display}"
        label_pad = max(0, W - 2 - len(title_label))
        print(f"{Fore.GREEN}║{Style.BRIGHT}{Fore.WHITE}{title_label}{' ' * label_pad}{Style.RESET_ALL}{Fore.GREEN}║")

        nmap_ok = "[OK] Nmap" if nmap_executed else "[--] Nmap"
        web_ok = f"[OK] Web ({active_protocol.replace('://', '')})" if has_web_flags else "[--] Web"
        vhost_ok = f"[OK] VHost ({active_domain})" if active_domain else "[--] VHost"
        ws_label = f"  Workspace: {workspace_dir}/"

        nmap_c = Fore.GREEN if nmap_executed else Fore.RED
        web_c = Fore.GREEN if has_web_flags else Fore.RED
        vhost_c = Fore.MAGENTA if active_domain else Fore.YELLOW

        print(f"{Fore.GREEN}╠{'─' * (W-2)}╣")
        status_plain = f"  Estado > {nmap_ok}  {web_ok}  {vhost_ok}"
        status_color = f"  Estado > {nmap_c}{nmap_ok}{Style.RESET_ALL}  {web_c}{web_ok}{Style.RESET_ALL}  {vhost_c}{vhost_ok}{Style.RESET_ALL}"
        status_pad = max(0, W - 2 - len(status_plain))
        print(f"{Fore.GREEN}║{status_color}{' ' * status_pad}")
        ws_pad = max(0, W - 2 - len(ws_label))
        print(f"{Fore.GREEN}║{Fore.CYAN}{ws_label}{' ' * ws_pad}")
        print(f"{Fore.GREEN}╚{'═' * (W-2)}╝{Style.RESET_ALL}")

        _section("FASE 1 -- RECONOCIMIENTO & ESCANEO", color=Fore.CYAN)
        _opt(1, "Fingerprint de SO (Ping TTL)")
        nmap_status = _badge("[OK] COMPLETADO", Fore.GREEN) if nmap_executed else _badge("<-- EMPIEZA AQUI", Fore.YELLOW)
        _opt(2, "Escaneo de Puertos y Servicios (Nmap)", status=nmap_status)
        _opt(3, "Entornos Windows (Enum4Linux)")

        _section("FASE 2 -- ENUMERACION WEB", color=Fore.CYAN)
        if not nmap_executed:
            _warn("Ejecuta Nmap (2) primero para calibrar protocolo y dominio.")
        elif not has_web_flags:
            _warn("Nmap no detecto HTTP/HTTPS. Las herramientas web podrian fallar.")
        _opt(4, "Enumeracion de Directorios Web (Gobuster)")
        ffuf_status = _badge("DOMINIO ACTIVO", Fore.GREEN) if active_domain else _badge("Requiere Dominio", Fore.RED)
        _opt(5, "Descubrimiento de Subdominios (FFuF)", status=ffuf_status)
        _opt(6, "Scanner CMS WordPress (WPScan)")
        _opt(7, "Inyecciones SQL Dinamicas (SQLMap)")
        _opt(8, "Scanner CVEs Modernos (Nuclei)")
        _opt(9, "Vulnerabilidades Web Clasicas (Nikto)")

        _section("FASE 3 -- EXPLOTACION & POST-EXPLOTACION", color=Fore.RED)
        _opt(10, "Busqueda de Exploits Publicos (SearchSploit)")
        _opt(11, "Fuerza Bruta de Autenticacion (Hydra FTP/SSH)")
        _opt(12, "Cracking de Hashes Offline (John The Ripper)")
        _opt(13, "Descargar PEAS (Escalada de Privilegios Locales)")
        _opt(14, "Servidor HTTP de Transferencia de Payloads")
        _opt(15, "Abrir Puerto de Escucha Netcat (Reverse Shell)")

        _section("REPORTING & SALIDA", color=Fore.MAGENTA)
        _opt(16, "Compilar y Abrir Reporte HTML Maestro")
        _opt(17, "Generar Reporte PDF Profesional")
        _opt(18, "Generar Reporte DOCX Profesional")
        _opt(19, "Ver Histórico y Diff de Escaneos (DB)")
        _opt(20, "Volver al Menu Principal")

        print()
        _line("─")
        opcion = _prompt("Selección")

        if opcion == '1':
            detect_os(ip, workspace_dir)
        elif opcion == '2':
            nmap_state = run_nmap(ip, workspace_dir)
            nmap_executed = True
            has_web_flags = nmap_state.get('has_web', False)
            active_protocol = nmap_state.get('web_protocol', 'http://')
            found_domains = nmap_state.get('domains', [])
            if found_domains:
                active_domain = found_domains[0]
                active_target = active_domain
                _ok(f"Dominio detectado y guardado: {active_domain}  →  VHOST Activado.")
            # Persistir puertos abiertos en DB
            _persist_nmap(scan_id, workspace_dir)
        elif opcion == '3':
            run_enum4linux(ip, workspace_dir)
        elif opcion == '4':
            if not nmap_executed:
                _err("Ejecuta Nmap (opción 2) primero.")
            else:
                run_web_enum(active_target, active_protocol, workspace_dir)
        elif opcion == '5':
            run_ffuf_subdomains(active_target, active_protocol, active_domain, workspace_dir)
        elif opcion == '6':
            if not nmap_executed:
                _err("Ejecuta Nmap (opción 2) primero.")
            else:
                run_wpscan(active_target, active_protocol, workspace_dir)
        elif opcion == '7':
            run_sqlmap(workspace_dir)
        elif opcion == '8':
            if not nmap_executed:
                _err("Ejecuta Nmap (opcion 2) primero.")
            else:
                run_nuclei(active_target, active_protocol, workspace_dir)
                _persist_nuclei(scan_id, workspace_dir)
        elif opcion == '9':
            if not nmap_executed:
                _err("Ejecuta Nmap (opcion 2) primero.")
            else:
                run_nikto(active_target, active_protocol, workspace_dir)
        elif opcion == '10':
            run_searchsploit(workspace_dir)
        elif opcion == '11':
            run_hydra_bruteforce(ip, workspace_dir)
        elif opcion == '12':
            run_hash_cracking(workspace_dir)
        elif opcion == '13':
            download_peas(workspace_dir)
        elif opcion == '14':
            start_http_server_payloads(workspace_dir)
        elif opcion == '15':
            run_netcat_listener(workspace_dir)
        elif opcion == '16':
            generate_html_report(ip, active_domain, workspace_dir)
        elif opcion == '17':
            path = generate_pdf_report(scan_id, workspace_dir, ip)
            if path:
                _ok(f"PDF generado: {path}")
            else:
                _err("Error generando PDF. ¿Está instalado WeasyPrint?")
        elif opcion == '18':
            path = generate_docx_report(scan_id, workspace_dir, ip)
            if path:
                _ok(f"DOCX generado: {path}")
            else:
                _err("Error generando DOCX. ¿Está instalado python-docx?")
        elif opcion == '19':
            if project_id:
                _show_history_and_diff(project_id)
            else:
                _info("No hay proyecto activo. Reinicia y asocia un cliente para ver el histórico.")
        elif opcion == '20':
            finish_scan(scan_id, status="completed")
            break
        else:
            _err("Opcion no reconocida. Introduce el numero correspondiente.")

        input(f"\n  {Fore.CYAN}[Pulsa ENTER para continuar...]{Style.RESET_ALL}")


def main():
    """Función principal: parsea CLI flags y arranca el menú interactivo."""
    parser = argparse.ArgumentParser(
        prog="fr4meluc",
        description="Fr4meLuc — Educational Pentesting Framework (CLI)",
    )
    parser.add_argument("--quiet", action="store_true",
                        help="Desactiva la capa educativa (edu_print). Útil para uso profesional.")
    parser.add_argument("--daemon", action="store_true",
                        help="Ejecuta el daemon de scheduling en segundo plano (APScheduler).")
    parser.add_argument("--report-pdf", type=int, metavar="SCAN_ID",
                        help="Genera un reporte PDF para el scan_id indicado y sale.")
    parser.add_argument("--report-docx", type=int, metavar="SCAN_ID",
                        help="Genera un reporte DOCX para el scan_id indicado y sale.")
    args = parser.parse_args()

    init(autoreset=True)
    if args.quiet:
        set_educational(False)

    if args.daemon:
        from ..core.daemon import run_daemon
        run_daemon()
        return  # run_daemon blocks; this return is never reached normally

    if args.report_pdf is not None:
        init_db()
        scan = get_scan(args.report_pdf)
        if scan is None:
            _err(f"Scan ID {args.report_pdf} no encontrado en la DB.")
            sys.exit(1)
        path = generate_pdf_report(args.report_pdf, scan['workspace_dir'], scan['target'])
        if path:
            _ok(f"PDF generado: {path}")
        sys.exit(0)

    if args.report_docx is not None:
        init_db()
        scan = get_scan(args.report_docx)
        if scan is None:
            _err(f"Scan ID {args.report_docx} no encontrado en la DB.")
            sys.exit(1)
        path = generate_docx_report(args.report_docx, scan['workspace_dir'], scan['target'])
        if path:
            _ok(f"DOCX generado: {path}")
        sys.exit(0)

    init_db()

    try:
        print_banner()
        check_dependencies()

        while True:
            _box_title("MENU PRINCIPAL", Fore.BLUE)

            _section("Reconocimiento", color=Fore.CYAN)
            _opt(1, "Escanear Red Local (ARP Scan)")

            _section("Objetivo", color=Fore.CYAN)
            _opt(2, "Configurar Host Objetivo Manualmente")

            _section("Sistema", color=Fore.CYAN)
            _opt(3, "Salir del Framework")

            print()
            _line("-")
            opcion = _prompt("Seleccion")

            if opcion == '1':
                do_arp_scan(target_menu)
            elif opcion == '2':
                _line("-", Fore.CYAN)
                ip = _prompt("Introduce la IP objetivo  (ej. 192.168.1.50)")
                if ip:
                    if not validate_target(ip):
                        _err(f"'{ip}' no es una IP ni hostname valido. Ejemplo: 192.168.1.5 o maquina.htb")
                    else:
                        target_menu(ip)
                else:
                    _err("La IP no puede estar vacia.")
            elif opcion == '3':
                print()
                _ok("¡Hasta pronto! Gracias por usar el Framework.")
                print()
                sys.exit(0)
            else:
                _err("Opción no reconocida. Por favor introduce un número del menú.")

            time.sleep(1.2)

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Interrupción por teclado (Ctrl+C) detectada. Cerrando framework...{Style.RESET_ALL}")
        sys.exit(0)


if __name__ == "__main__":
    main()
