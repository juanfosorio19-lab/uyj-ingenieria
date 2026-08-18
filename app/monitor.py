"""Vigilancia intradía: cada 15 minutos con mercado abierto.

    python -m app.monitor

- Registra heartbeat en cada ciclo (arma el dead man's switch: si este
  proceso muere, las compras nuevas se bloquean solas).
- Con mercado abierto, evalúa las reglas de salida deterministas y ejecuta
  ventas defensivas.
"""

import logging
import time

from app.brokers.factory import make_adapter
from app.controls import record_heartbeat
from app.db import get_engine, init_db, make_session_factory
from app.exits import check_and_execute_exits
from app.report import send_telegram_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # sus INFO imprimen URLs con el token del bot
log = logging.getLogger(__name__)

CYCLE_SECONDS = 15 * 60


def main() -> None:
    engine = get_engine()
    init_db(engine)
    session_factory = make_session_factory(engine)
    adapter = make_adapter(session_factory)
    log.info(
        "Monitor corriendo (broker=%s): heartbeat + ventas defensivas cada 15 min. "
        "Dead man's switch ARMADO desde ahora.",
        adapter.name,
    )
    while True:
        record_heartbeat(session_factory, key="monitor")
        try:
            if adapter.is_market_open():
                for message in check_and_execute_exits(session_factory, adapter):
                    send_telegram_message(message)
        except Exception:
            log.exception("Ciclo de monitoreo falló; se reintenta en el próximo")
        time.sleep(CYCLE_SECONDS)


if __name__ == "__main__":
    main()
