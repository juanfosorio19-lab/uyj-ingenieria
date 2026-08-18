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
logging.getLogger("httpx").setLevel(logging.WARNING)  # sus INFO imprimen URLs con el token del bot
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
    from app.brokers.factory import make_adapter

    sf = _session_factory()
    try:
        adapter = make_adapter(sf)
    except RuntimeError:  # BROKER=alpaca sin keys: el reporte usa el paper interno
        adapter = None
    text = build_daily_report(sf, adapter=adapter)
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
    from app.eligibility import build_eligibility

    eligible = build_eligibility(sf, closes)
    if eligible is not None:
        log.info("Backtest con máscara point-in-time (universo/fundamentales cargados)")
    try:
        result = run_backtest(closes, eligible=eligible)
    except ValueError as exc:
        log.error("Backtest no ejecutable: %s", exc)
        return str(exc)
    path = write_report(result)
    text = summary_text(result)
    send_telegram_message(text)
    send_telegram_document(path, caption="Reporte completo del backtest")
    log.info("Backtest listo: %s (reporte en %s)", "PASA" if result.passed else "NO pasa", path)
    return text


def run_propose() -> str:
    """Fase 3: el analista propone, el Risk Engine veredicta, Telegram informa."""
    from app.llm.analyst import analyze
    from app.report import send_telegram_message
    from app.risk import evaluate_from_db

    sf = _session_factory()
    outcome = analyze(sf)
    if outcome.status == "no_data":
        msg = "🤖 Sin datos suficientes para proponer (corre la ingesta primero)."
    elif outcome.status == "rejected_schema":
        msg = "🤖 Propuesta RECHAZADA por formato inválido del analista (auditada, no ejecutada)."
    elif outcome.status == "error":
        msg = "🤖 El analista falló hoy; queda registrado. Sin propuesta."
    else:
        p = outcome.proposal
        verdict = evaluate_from_db(sf, p)
        if p.action == "hold":
            msg = f"🤖 Propuesta del día: MANTENER.\nRazón: {p.thesis}"
        else:
            invalidators = "; ".join(
                f"{i.metric} {i.op} {i.value}" for i in p.invalidators
            )
            msg = (
                f"🤖 Propuesta del día: COMPRAR {p.symbol} "
                f"({p.max_position_pct:.0%} del portafolio)\n"
                f"Tesis: {p.thesis}\n"
                f"Invalidadores: {invalidators}\n"
                f"Horizonte: {p.target_horizon_days} días · Confianza: {p.confidence:.2f}\n"
                f"🛡️ Risk Engine: {verdict.summary}\n"
                f"(fase 3: solo propone — la ejecución llega en la fase 4)"
            )
    send_telegram_message(msg)
    log.info("Propuesta del día enviada")
    return msg


def run_trade() -> str:
    """Fase 4: decide y EJECUTA en el broker configurado (con reconciliación)."""
    from app.brokers.factory import make_adapter
    from app.report import send_telegram_message
    from app.trade import trade_once

    sf = _session_factory()
    adapter = make_adapter(sf)
    msg = trade_once(sf, adapter)
    send_telegram_message(msg)
    log.info("Ciclo de trading (%s) completado", adapter.name)
    return msg


def run_exits() -> str:
    """Evalúa y ejecuta las salidas defensivas (también lo hace el monitor)."""
    from app.brokers.factory import make_adapter
    from app.exits import check_and_execute_exits
    from app.report import send_telegram_message

    sf = _session_factory()
    adapter = make_adapter(sf)
    messages = check_and_execute_exits(sf, adapter)
    for message in messages:
        send_telegram_message(message)
    result = f"{len(messages)} salidas defensivas" if messages else "Sin salidas que ejecutar"
    log.info(result)
    return result


def run_fundamentals() -> str:
    """Descarga fundamentales SEC EDGAR (con fecha de publicación) del universo."""
    from app.data.edgar import ingest_fundamentals

    sf = _session_factory()
    symbols = [s for s in ensure_universe(sf) if s != "SPY"]
    log.info("Bajando fundamentales de EDGAR para %d símbolos (varios minutos)...", len(symbols))
    msg = ingest_fundamentals(sf, symbols)
    log.info(msg)
    return msg


def run_universe_load() -> str:
    """Carga constituyentes históricos: python -m app.jobs universe-load archivo.csv"""
    from app.universe import load_universe_csv

    if len(sys.argv) < 3:
        return "Uso: python -m app.jobs universe-load <archivo.csv>"
    msg = load_universe_csv(_session_factory(), sys.argv[2])
    log.info(msg)
    return msg


def run_daily() -> None:
    from app.brokers.factory import make_adapter
    from app.config import get_settings
    from app.trade import snapshot_portfolio

    ingest_result = run_ingest()
    run_fx()
    run_report()
    if get_settings().execution_enabled:
        run_exits()  # primero proteger lo que hay...
        run_trade()  # ...después decidir lo nuevo
    else:
        run_propose()  # fase 3: solo propone
    try:
        sf = _session_factory()
        snapshot_portfolio(sf, make_adapter(sf))
    except Exception:
        log.exception("No se pudo tomar el snapshot del portafolio")
    log.info("Ciclo diario completo (%s)", ingest_result)


def main() -> None:
    commands = {
        "ingest": run_ingest,
        "fx": run_fx,
        "report": run_report,
        "daily": run_daily,
        "backtest": run_backtest_job,
        "propose": run_propose,
        "trade": run_trade,
        "exits": run_exits,
        "fundamentals": run_fundamentals,
        "universe-load": run_universe_load,
    }
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    job = commands.get(name)
    if job is None:
        print(f"Uso: python -m app.jobs [{'|'.join(commands)}]")
        raise SystemExit(1)
    job()


if __name__ == "__main__":
    main()
