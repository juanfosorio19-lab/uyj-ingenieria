"""Bot de Telegram — la cara visible de la fase 0.

Comandos: /status /buy /sell /kill /resume /help
Si TELEGRAM_CHAT_ID está definido, ignora cualquier otro chat.
"""

import uuid
from decimal import Decimal, InvalidOperation

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.brokers.base import OrderRejected
from app.brokers.paper import PaperAdapter
from app.config import get_settings
from app.controls import orders_enabled, set_orders_enabled
from app.db import get_engine, init_db, make_session_factory


def _authorized(update: Update) -> bool:
    allowed = get_settings().telegram_chat_id
    if not allowed:
        return True
    return update.effective_chat is not None and str(update.effective_chat.id) == allowed


def _build_handlers(adapter: PaperAdapter, session_factory):
    async def status(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not _authorized(update):
            return
        positions = adapter.get_positions()
        lines = [
            f"Broker: {adapter.name}",
            f"Caja: USD {adapter.get_cash():,.2f}",
            f"Órdenes: {'habilitadas ✅' if orders_enabled(session_factory) else 'BLOQUEADAS 🛑'}",
            f"Mercado NYSE: {'abierto 🟢' if adapter.is_market_open() else 'cerrado ⚪'}",
        ]
        if positions:
            lines.append("\nPosiciones:")
            lines += [
                f"  {p.symbol}: {p.qty:g} @ USD {p.avg_price_usd:,.2f}" for p in positions
            ]
        else:
            lines.append("\nSin posiciones.")
        await update.message.reply_text("\n".join(lines))

    async def _trade(update: Update, context: ContextTypes.DEFAULT_TYPE, side: str) -> None:
        if not _authorized(update):
            return
        args = context.args or []
        if len(args) < 2:
            await update.message.reply_text(
                f"Uso: /{side} SIMBOLO CANTIDAD [PRECIO]\nEj: /{side} AAPL 10 230.50"
            )
            return
        try:
            qty = Decimal(args[1])
            price = Decimal(args[2]) if len(args) > 2 else None
        except InvalidOperation:
            await update.message.reply_text("Cantidad o precio inválido.")
            return
        try:
            result = adapter.place_order(
                symbol=args[0], side=side, qty=qty, idempotency_key=str(uuid.uuid4()), price=price
            )
        except OrderRejected as exc:
            await update.message.reply_text(f"❌ Rechazada: {exc}")
            return
        verb = "Comprado" if side == "buy" else "Vendido"
        await update.message.reply_text(
            f"✅ {verb} {result.qty:g} {result.symbol} @ USD {result.fill_price_usd:,.2f} (paper)"
        )

    async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _trade(update, context, "buy")

    async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _trade(update, context, "sell")

    async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not _authorized(update):
            return
        reason = " ".join(context.args or []) or "manual desde Telegram"
        set_orders_enabled(session_factory, False, actor="telegram", reason=reason)
        await update.message.reply_text("🛑 Kill switch ACTIVADO. Nada se ejecuta hasta /resume.")

    async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not _authorized(update):
            return
        reason = " ".join(context.args or []) or "manual desde Telegram"
        set_orders_enabled(session_factory, True, actor="telegram", reason=reason)
        await update.message.reply_text("✅ Órdenes habilitadas nuevamente.")

    async def help_cmd(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not _authorized(update):
            return
        await update.message.reply_text(
            "/status — caja, posiciones, estado del sistema\n"
            "/buy SIMBOLO CANTIDAD [PRECIO] — compra simulada\n"
            "/sell SIMBOLO CANTIDAD [PRECIO] — venta simulada\n"
            "/kill [razón] — detener todas las órdenes\n"
            "/resume [razón] — rehabilitar órdenes"
        )

    return {
        "status": status,
        "buy": buy,
        "sell": sell,
        "kill": kill,
        "resume": resume,
        "help": help_cmd,
    }


def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN no configurado; el bot no se inicia.")
        print("Crea un bot con @BotFather en Telegram y pega el token en .env")
        return

    engine = get_engine()
    init_db(engine)
    session_factory = make_session_factory(engine)
    adapter = PaperAdapter(session_factory)

    application = Application.builder().token(settings.telegram_bot_token).build()
    for command, handler in _build_handlers(adapter, session_factory).items():
        application.add_handler(CommandHandler(command, handler))

    print("Bot de Telegram corriendo (long polling)...")
    application.run_polling()


if __name__ == "__main__":
    main()
