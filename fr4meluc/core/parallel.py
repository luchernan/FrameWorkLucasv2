"""Ejecución paralela de escaneos automáticos sobre múltiples targets.

Usa ThreadPoolExecutor (no ProcessPoolExecutor): el trabajo es I/O-bound
(subprocess + DB SQLite), y los hilos comparten el módulo sin coste de pickling.

Garantía de aislamiento: una excepción en un target NUNCA aborta los demás.
Cada worker captura todo, marca su scan como 'error' y registra en stderr.
"""

import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from .workspace import create_workspace
from .storage import create_scan, finish_scan
from .parsers import parse_nmap
from .pipeline import run_pipeline


def _scan_one(target: str, project_id, profile: str) -> int:
    """Procesa un único target de principio a fin. Devuelve el scan_id.

    Pasos:
      1. Crear workspace.
      2. Registrar el scan en la DB.
      3. Parsear nmap.xml si existe; si no, ports = [].
      4. Ejecutar el pipeline automático.
      5. Marcar el scan como 'completed'.

    En caso de error después de crear el scan, lo marca como 'error' con la
    traza y re-lanza para que el llamador lo registre — pero create_scan ya
    garantiza que el scan_id existe para el reporte.
    """
    workspace_dir = create_workspace(target)
    if workspace_dir is None:
        # Sin workspace no hay dónde guardar evidencia: fallo explícito.
        raise RuntimeError(f"No se pudo crear el workspace para '{target}' (permisos).")

    scan_id = create_scan(target, workspace_dir, project_id=project_id, profile=profile)

    try:
        nmap_xml = os.path.join(workspace_dir, "nmap", "nmap.xml")
        ports = parse_nmap(nmap_xml) if os.path.exists(nmap_xml) else []

        run_pipeline(ports, workspace_dir, target, scan_id)
        finish_scan(scan_id, status="completed")
        return scan_id
    except Exception as exc:  # noqa: BLE001 — aislamos el worker deliberadamente
        # Persistir el fallo en el scan ya creado antes de propagar.
        finish_scan(scan_id, status="error", notes=str(exc))
        sys.stderr.write(
            f"[parallel] Error procesando target '{target}' (scan {scan_id}): {exc}\n"
        )
        sys.stderr.write(traceback.format_exc())
        # Devolvemos el scan_id igualmente: el scan existe y quedó marcado 'error'.
        return scan_id


def run_parallel(targets: list, project_id=None, profile: str = "auto",
                 max_workers: int = 4) -> list:
    """Lanza escaneos automáticos en paralelo sobre `targets`.

    Args:
        targets: lista de IPs/hosts.
        project_id: id de proyecto en la DB (o None para anónimo).
        profile: etiqueta de perfil para el registro del scan.
        max_workers: hilos concurrentes (ThreadPoolExecutor).

    Returns:
        Lista de scan_ids en orden de finalización (as_completed).
        Incluye los scans que terminaron en 'error' (su id es válido).
    """
    clean_targets = [t for t in (targets or []) if t and str(t).strip()]
    if not clean_targets:
        return []

    # max_workers debe ser >= 1; nunca más que el número de targets.
    workers = max(1, min(max_workers, len(clean_targets)))

    scan_ids: list = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_target = {
            executor.submit(_scan_one, t.strip(), project_id, profile): t.strip()
            for t in clean_targets
        }
        for future in as_completed(future_to_target):
            target = future_to_target[future]
            try:
                scan_id = future.result()
                scan_ids.append(scan_id)
            except Exception as exc:  # noqa: BLE001 — un target no debe tumbar el batch
                # Esto solo ocurre si _scan_one falló ANTES de crear el scan
                # (p.ej. create_workspace devolvió None). No hay scan_id que devolver.
                sys.stderr.write(
                    f"[parallel] Target '{target}' falló sin scan registrado: {exc}\n"
                )
                sys.stderr.write(traceback.format_exc())

    return scan_ids
