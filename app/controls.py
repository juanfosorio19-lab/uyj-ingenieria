"""Kill switch: el flag vive en la base de datos, fuera del alcance del LLM."""

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
