"""Kill switch y heartbeats: flags en la base de datos, fuera del alcance del LLM."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.models import KillSwitchEvent, SystemFlag


def orders_enabled(session_factory: sessionmaker[Session]) -> bool:
    with session_factory() as s:
        flag = s.get(SystemFlag, "orders_enabled")
        return flag is None or flag.value == "true"


def set_orders_enabled(
    session_factory: sessionmaker[Session], enabled: bool, actor: str, reason: str = ""
) -> None:
    with session_factory() as s:
        flag = s.get(SystemFlag, "orders_enabled")
        if flag is None:
            flag = SystemFlag(key="orders_enabled", value="")
            s.add(flag)
        flag.value = "true" if enabled else "false"
        s.add(
            KillSwitchEvent(
                actor=actor, action="resume" if enabled else "halt", reason=reason
            )
        )
        s.commit()


def record_heartbeat(session_factory: sessionmaker[Session], key: str = "monitor") -> None:
    """El proceso de vigilancia declara que está vivo. Arma el dead man's switch."""
    with session_factory() as s:
        flag = s.get(SystemFlag, f"heartbeat_{key}")
        if flag is None:
            flag = SystemFlag(key=f"heartbeat_{key}", value="")
            s.add(flag)
        flag.value = datetime.now(UTC).isoformat()
        s.commit()


def heartbeat_age_seconds(
    session_factory: sessionmaker[Session], key: str = "monitor"
) -> float | None:
    """Segundos desde el último latido; None si el DMS nunca se armó."""
    with session_factory() as s:
        flag = s.get(SystemFlag, f"heartbeat_{key}")
    if flag is None or not flag.value:
        return None
    last = datetime.fromisoformat(flag.value)
    return (datetime.now(UTC) - last).total_seconds()
