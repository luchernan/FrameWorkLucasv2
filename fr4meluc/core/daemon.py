"""Daemon de scheduling de Fr4meLuc — ejecuta jobs cron con APScheduler.

Lee los jobs de la tabla scheduler_jobs y programa cada uno con un CronTrigger.
Bloquea el proceso indefinidamente; SIGINT/SIGTERM apagan el scheduler limpio.

Logging dual: consola (StreamHandler INFO) + archivo rotatorio
(RotatingFileHandler sobre fr4meluc-daemon.log en el cwd).
"""

import sys
import time
import signal
import logging
from logging.handlers import RotatingFileHandler

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import init_db
from .storage import list_scheduler_jobs, update_job_last_run
from .parallel import run_parallel

_LOG_FILE = "fr4meluc-daemon.log"
_LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_LOG_BACKUPS = 3

logger = logging.getLogger("fr4meluc.daemon")


class _JsonFormatter(logging.Formatter):
    """Formatea cada registro de log como una línea JSON.

    Campos: ts (ISO-8601 UTC), level, msg.
    Uso: RotatingFileHandler + StreamHandler para daemon.
    """

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"
        payload = {
            "ts": ts,
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)


def _setup_logging() -> None:
    """Configura logging dual (consola + archivo rotatorio).

    Idempotente: limpia handlers previos para evitar duplicados si se reinvoca.
    """
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Evitar handlers duplicados en re-arranques dentro del mismo proceso.
    for existing in list(logger.handlers):
        logger.removeHandler(existing)

    fmt = _JsonFormatter()

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUPS,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)


def _parse_targets(raw: str) -> list:
    """Convierte el CSV de targets de un job en una lista limpia."""
    if not raw:
        return []
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def _run_job(job: dict) -> None:
    """Ejecuta un job programado: lanza run_parallel sobre sus targets.

    Captura todas las excepciones — un job que falla NUNCA debe tumbar el
    scheduler ni los demás jobs.
    """
    name = job.get("name", f"job_{job.get('id')}")
    try:
        targets = _parse_targets(job.get("targets", ""))
        logger.info("Running job %s — targets: %s", name, targets)

        if not targets:
            logger.warning("Job %s no tiene targets válidos; se omite.", name)
            return

        scan_ids = run_parallel(
            targets,
            project_id=job.get("project_id"),
            profile=job.get("profile", "auto"),
        )

        update_job_last_run(job["id"])
        logger.info("Job %s completed. Scans: %s", name, scan_ids)
    except Exception as exc:  # noqa: BLE001 — un job no debe abortar el daemon
        logger.error("Job %s falló: %s", name, exc, exc_info=True)


def run_daemon() -> None:
    """Arranca el daemon de scheduling y bloquea hasta SIGINT/SIGTERM."""
    _setup_logging()
    init_db()

    jobs = list_scheduler_jobs()
    scheduler = BackgroundScheduler()

    loaded = 0
    for job in jobs:
        cron_expr = job.get("cron_expr")
        if not cron_expr:
            logger.warning("Job %s sin cron_expr; se omite.", job.get("name"))
            continue
        try:
            trigger = CronTrigger.from_crontab(cron_expr)
        except ValueError as exc:
            logger.error(
                "Cron inválido para job %s ('%s'): %s",
                job.get("name"), cron_expr, exc,
            )
            continue

        scheduler.add_job(
            _run_job,
            trigger=trigger,
            args=[job],
            id=f"job_{job['id']}",
            max_instances=1,
            replace_existing=True,
        )
        loaded += 1

    scheduler.start()
    logger.info("Fr4meLuc daemon started. %s jobs loaded.", loaded)

    def _shutdown(signum, _frame):
        logger.info("Señal %s recibida; apagando scheduler...", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Bloqueo principal. El sleep mantiene el hilo principal vivo mientras
    # APScheduler ejecuta los jobs en su BackgroundScheduler.
    while True:
        time.sleep(60)
