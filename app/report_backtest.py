"""Reporte HTML del backtest — el entregable visible de la fase 2."""

from pathlib import Path

import pandas as pd

from app.backtest import BacktestResult

REPORT_PATH = Path("reports/backtest.html")


def _svg_equity_chart(strategy: pd.Series, bench: pd.Series, width=760, height=300) -> str:
    """Curvas de equity normalizadas a 100, SVG hecho a mano (sin dependencias)."""

    def polyline(series: pd.Series, color: str) -> str:
        values = (series / series.iloc[0] * 100).tolist()
        lo = min(values)
        hi = max(values)
        span = (hi - lo) or 1.0
        points = " ".join(
            f"{(i / (len(values) - 1)) * (width - 60) + 50:.1f},"
            f"{height - 30 - ((v - lo) / span) * (height - 60):.1f}"
            for i, v in enumerate(values)
        )
        return f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points}"/>'

    return (
        f'<svg viewBox="0 0 {width} {height}" style="max-width:100%;background:#fafafa">'
        f'<text x="50" y="20" font-size="12" fill="#2563eb">— Estrategia</text>'
        f'<text x="150" y="20" font-size="12" fill="#6b7280">— SPY (buy&amp;hold)</text>'
        + polyline(bench, "#6b7280")
        + polyline(strategy, "#2563eb")
        + "</svg>"
    )


def summary_text(result: BacktestResult) -> str:
    """Resumen corto para Telegram."""
    verdict = "✅ PASA (≥3 de 4 ventanas)" if result.passed else "❌ NO PASA todavía"
    lines = [
        "🧪 Backtest walk-forward (después de costos)",
        f"Estrategia: {result.strategy_total:+.1%} · SPY: {result.benchmark_total:+.1%}",
        f"Ventanas ganadas: {result.wins}/{len(result.windows)} → {verdict}",
        f"Sharpe: {result.sharpe:.2f} · Max drawdown: {result.max_drawdown:.1%}",
        f"Costos acumulados: {result.total_costs_pct:.1%}",
        "⚠️ Provisorio: universo sin constituyentes históricos (survivorship bias)",
    ]
    return "\n".join(lines)


def build_backtest_html(result: BacktestResult) -> str:
    rows = "".join(
        f"<tr><td>{w.start} → {w.end}</td>"
        f"<td>{w.strategy_return:+.1%}</td><td>{w.benchmark_return:+.1%}</td>"
        f"<td>{'✅' if w.beats else '❌'}</td></tr>"
        for w in result.windows
    )
    verdict = (
        '<b style="color:#16a34a">PASA el criterio de la fase 2</b>'
        if result.passed
        else '<b style="color:#dc2626">NO pasa todavía</b>'
    )
    cfg = result.config
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Backtest — agente de trading</title>
<style>body{{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem;color:#111}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}}
th{{background:#f3f4f6}}.warn{{background:#fef9c3;padding:.7rem;border-radius:6px}}</style></head><body>
<h1>Backtest walk-forward</h1>
<p>Hipótesis (declarada antes de mirar datos): top {cfg.top_n} por momentum 6m−1m,
equiponderado, rebalanceo mensual, costos {cfg.cost_per_side:.1%} por lado.</p>
{_svg_equity_chart(result.equity, result.bench_equity)}
<h2>Resultado: {verdict}</h2>
<table><tr><th>Ventana</th><th>Estrategia</th><th>SPY</th><th>¿Bate?</th></tr>{rows}</table>
<p>Total estrategia: <b>{result.strategy_total:+.1%}</b> · SPY: <b>{result.benchmark_total:+.1%}</b>
· Sharpe {result.sharpe:.2f} · Max DD {result.max_drawdown:.1%}
· Costos acumulados {result.total_costs_pct:.1%}</p>
<p class="warn">⚠️ Resultado provisorio: el universo actual es la lista de hoy
(survivorship bias) y los factores fundamentales aún no entran (falta SEC EDGAR
point-in-time). El criterio de salida definitivo de la fase 2 se evalúa cuando
eso esté cargado. Ver docs/PLAN-FASES.md.</p>
</body></html>"""


def write_report(result: BacktestResult, path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_backtest_html(result), encoding="utf-8")
    return path
