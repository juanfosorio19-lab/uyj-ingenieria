"""Programador simple: corre el ciclo diario después del cierre de NYSE.

    python -m app.scheduler

Días hábiles a las 16:45 hora de Nueva York (≈17:45–18:45 hora de Chile).
Fuera de esa ventana duerme: el agente trabaja cuando el mercado trabaja.
En el VPS (fase 4) esto mismo lo dispara n8n contra la API; aquí basta un
proceso. TODO fase 1.1: saltar feriados NYSE.
"""

import logging
import time as time_module
from datetime import datetime, time, timedelta

from app.jobs import run_daily
from app.market_hours import NYSE_TZ

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

RUN_AT = time(16, 45)  # 45 min después del cierre, hora de Nueva York


def next_run(now: datetime) -> datetime:
    """Próximo día hábil a las RUN_AT (hora NY)."""
    now = now.astimezone(NYSE_TZ)
    candidate = now.replace(
        hour=RUN_AT.hour, minute=RUN_AT.minute, second=0, microsecond=0
    )
    if now >= candidate:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:  # sábado/domingo
        candidate += timedelta(days=1)
    return candidate


def main() -> None:
    log.info("Scheduler corriendo: ciclo diario a las %s NY, días hábiles.", RUN_AT)
    while True:
        target = next_run(datetime.now(NYSE_TZ))
        wait = (target - datetime.now(NYSE_TZ)).total_seconds()
        log.info("Próxima corrida: %s (en %.1f horas)", target, wait / 3600)
        while wait > 0:
            time_module.sleep(min(wait, 300))
            wait = (target - datetime.now(NYSE_TZ)).total_seconds()
        try:
            run_daily()
        except Exception:
            log.exception("El ciclo diario falló; se reintenta en la próxima corrida")


if __name__ == "__main__":
    main()
