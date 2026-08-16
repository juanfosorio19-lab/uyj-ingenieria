from datetime import datetime, time
from zoneinfo import ZoneInfo

NYSE_TZ = ZoneInfo("America/New_York")
OPEN = time(9, 30)
CLOSE = time(16, 0)


def is_nyse_open(now: datetime | None = None) -> bool:
    """Lunes a viernes, 9:30–16:00 hora de Nueva York.

    TODO fase 1: calendario de feriados NYSE.
    """
    now = (now or datetime.now(NYSE_TZ)).astimezone(NYSE_TZ)
    return now.weekday() < 5 and OPEN <= now.time() < CLOSE
