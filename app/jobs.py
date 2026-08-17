"""Trabajos por línea de comandos.

    python -m app.jobs ingest   # backfill/actualización de precios del universo
    python -m app.jobs fx       # dólar observado del día
    python -m app.jobs report   # arma y envía el resumen diario a Telegram
    python -m app.jobs daily    # los tres en orden (lo que corre el scheduler)
"""

import logging
import sys

from app.data.fx import update_fx_rate
from app.data.ingest import YFinanceSource, ingest_universe
from app.db import get_engine, init_db, make_session_factory
from app.report import build_daily_report, send_telegram_message
from app.universe import ensure_universe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _session_factory():
    engine = get_engine()
    init_db(engine)
    return make_session_factory(engine)


def run_ingest() -> str:
    sf = _session_factory()
    symbols = ensure_universe(sf)
    log.info("Ingestando %d símbolos (la primera vez tarda varios minutos)...", len(symbols))
    summary = ingest_universe(sf, YFinanceSource(), symbols)
    log.info("Ingesta: %s", summary.one_liner())
    return summary.one_liner()


def run_fx() -> str:
    sf = _session_factory()
    result = update_fx_rate(sf)
    msg = f"Dólar observado: {result[1]} ({result[0]})" if result else "FX no disponible hoy"
    log.info(msg)
    return msg


def run_report() -> str:
    sf = _session_factory()
    text = build_daily_report(sf)
    sent = send_telegram_message(text)
    log.info("Reporte %s", "enviado a Telegram" if sent else "impreso en consola")
    return text


def run_backtest_job() -> str:
    """Fase 2: corre el backtest walk-forward y manda el reporte a Telegram."""
    from app.backtest import load_close_matrix, run_backtest
    from app.report import send_telegram_document, send_telegram_message
    from app.report_backtest import summary_text, write_report

    sf = _session_factory()
    closes = load_close_matrix(sf)
    if closes.empty:
        msg = "No hay precios en la base. Corre primero: python -m app.jobs ingest"
        log.error(msg)
        return msg
    try:
        result = run_backtest(closes)
    except ValueError as exc:
        log.error("Backtest no ejecutable: %s", exc)
        return str(exc)
    path = write_report(result)
    text = summary_text(result)
    send_telegram_message(text)
    send_telegram_document(path, caption="Reporte completo del backtest")
    log.info("Backtest listo: %s (reporte en %s)", "PASA" if result.passed else "NO pasa", path)
    return text


def run_daily() -> None:
    ingest_result = run_ingest()
    run_fx()
    run_report()
    log.info("Ciclo diario completo (%s)", ingest_result)


def main() -> None:
    commands = {
        "ingest": run_ingest,
        "fx": run_fx,
        "report": run_report,
        "daily": run_daily,
        "backtest": run_backtest_job,
    }
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    job = commands.get(name)
    if job is None:
        print(f"Uso: python -m app.jobs [{'|'.join(commands)}]")
        raise SystemExit(1)
    job()


if __name__ == "__main__":
    main()
