"""Dashboard web (fase 4): el agente a la vista, en localhost:8000."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.backtest import load_close_matrix
from app.config import get_settings
from app.controls import heartbeat_age_seconds, orders_enabled
from app.models import (
    AiDecision,
    Order,
    PortfolioSnapshot,
    Position,
    Reconciliation,
    Thesis,
)


def _svg_equity(snapshots: list[PortfolioSnapshot], width=740, height=200) -> str:
    if len(snapshots) < 2:
        return "<p>(la curva de equity aparece con ≥2 días de snapshots)</p>"
    values = [float(s.equity_usd) for s in snapshots]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    points = " ".join(
        f"{i / (len(values) - 1) * (width - 40) + 20:.1f},"
        f"{height - 20 - (v - lo) / span * (height - 40):.1f}"
        for i, v in enumerate(values)
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" style="max-width:100%;background:#fafafa">'
        f'<polyline fill="none" stroke="#2563eb" stroke-width="2" points="{points}"/></svg>'
    )


def build_dashboard_html(session_factory: sessionmaker[Session]) -> str:
    settings = get_settings()
    with session_factory() as s:
        positions = s.scalars(select(Position).order_by(Position.symbol)).all()
        snapshots = s.scalars(
            select(PortfolioSnapshot).order_by(PortfolioSnapshot.date)
        ).all()
        decisions = s.scalars(
            select(AiDecision).order_by(AiDecision.ts.desc()).limit(10)
        ).all()
        orders = s.scalars(select(Order).order_by(Order.created_at.desc()).limit(10)).all()
        recons = s.scalars(
            select(Reconciliation).order_by(Reconciliation.ts.desc()).limit(5)
        ).all()
        theses = s.scalars(
            select(Thesis).where(Thesis.status == "open").order_by(Thesis.created_at.desc())
        ).all()

    closes = load_close_matrix(session_factory)
    last_close = {}
    if not closes.empty:
        last_close = {c: Decimal(str(closes[c].dropna().iloc[-1])) for c in closes.columns}

    enabled = orders_enabled(session_factory)
    age = heartbeat_age_seconds(session_factory, key="monitor")
    if age is None:
        dms = "no armado (el monitor nunca ha corrido)"
    elif age > 45 * 60:
        dms = f"⚠️ CAÍDO: {age / 60:.0f} min sin latido"
    else:
        dms = f"vivo (latido hace {age / 60:.0f} min)"

    equity = snapshots[-1].equity_usd if snapshots else None

    def pos_row(p: Position) -> str:
        cur = last_close.get(p.symbol)
        pnl = ""
        if cur and Decimal(p.avg_price_usd) > 0:
            pct = (cur / Decimal(p.avg_price_usd) - 1) * 100
            color = "#16a34a" if pct >= 0 else "#dc2626"
            pnl = f'<td style="color:{color}">{pct:+.1f}%</td>'
        else:
            pnl = "<td>—</td>"
        return (
            f"<tr><td>{p.symbol}</td><td>{Decimal(p.qty):g}</td>"
            f"<td>{Decimal(p.avg_price_usd):,.2f}</td>"
            f"<td>{f'{cur:,.2f}' if cur else '—'}</td>{pnl}</tr>"
        )

    positions_html = (
        "<table><tr><th>Símbolo</th><th>Cantidad</th><th>Entrada</th>"
        "<th>Último cierre</th><th>P&L</th></tr>"
        + "".join(pos_row(p) for p in positions)
        + "</table>"
        if positions
        else "<p>Sin posiciones.</p>"
    )
    theses_html = (
        "".join(
            f"<li><b>{t.symbol}</b> ({t.created_at.date()}): {t.thesis[:180]}"
            f"<br><small>invalidadores: "
            + "; ".join(f"{i.get('metric')} {i.get('op')} {i.get('value')}"
                        for i in (t.invalidators or []))
            + f" · horizonte {t.target_horizon_days}d</small></li>"
            for t in theses
        )
        or "<li>Sin tesis abiertas.</li>"
    )
    decisions_html = "".join(
        f"<tr><td>{d.ts:%m-%d %H:%M}</td><td>{d.symbol}</td><td>{d.action}</td>"
        f"<td>{d.model_version}</td></tr>"
        for d in decisions
    )
    orders_html = "".join(
        f"<tr><td>{o.created_at:%m-%d %H:%M}</td><td>{o.side}</td><td>{o.symbol}</td>"
        f"<td>{Decimal(o.qty):g}</td><td>{o.status}</td></tr>"
        for o in orders
    )
    recons_html = "".join(
        f"<tr><td>{r.ts:%m-%d %H:%M}</td><td>{r.broker}</td>"
        f"<td>{'✅ ok' if r.status == 'ok' else '🛑 DIVERGENTE'}</td></tr>"
        for r in recons
    )

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="300"><title>Agente de trading</title>
<style>body{{font-family:system-ui,sans-serif;max-width:820px;margin:1.5rem auto;padding:0 1rem;color:#111}}
table{{border-collapse:collapse;width:100%;margin:.5rem 0}}td,th{{border:1px solid #ddd;padding:.35rem .5rem;text-align:left;font-size:.92rem}}
th{{background:#f3f4f6}}.card{{background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:.8rem 1rem;margin:.6rem 0}}
h2{{font-size:1.05rem;margin:1.2rem 0 .3rem}}</style></head><body>
<h1>🤖 Agente de trading</h1>
<div class="card">
Broker: <b>{settings.broker}</b> · Ejecución automática: <b>{"ON" if settings.execution_enabled else "off"}</b><br>
Órdenes: <b>{"habilitadas ✅" if enabled else "BLOQUEADAS 🛑"}</b> · Dead man's switch: <b>{dms}</b><br>
Equity (último snapshot): <b>{f"USD {equity:,.2f}" if equity is not None else "sin snapshot aún"}</b>
· Actualizado {datetime.now(UTC):%Y-%m-%d %H:%M} UTC</div>
<h2>Curva de equity</h2>{_svg_equity(snapshots)}
<h2>Posiciones</h2>{positions_html}
<h2>Tesis abiertas</h2><ul>{theses_html}</ul>
<h2>Últimas decisiones de IA</h2>
<table><tr><th>Fecha</th><th>Símbolo</th><th>Acción</th><th>Modelo</th></tr>{decisions_html}</table>
<h2>Últimas órdenes</h2>
<table><tr><th>Fecha</th><th>Lado</th><th>Símbolo</th><th>Cantidad</th><th>Estado</th></tr>{orders_html}</table>
<h2>Reconciliaciones</h2>
<table><tr><th>Fecha</th><th>Broker</th><th>Estado</th></tr>{recons_html}</table>
</body></html>"""
