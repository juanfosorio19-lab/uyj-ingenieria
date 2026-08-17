from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración por variables de entorno o archivo .env (ver .env.example)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "sqlite:///./data/agent.db"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""  # si se define, el bot ignora cualquier otro chat
    broker: str = "paper"
    starting_cash_usd: str = "10000"
    anthropic_api_key: str = ""  # sin key, el analista usa reglas (sin IA)
    llm_model: str = "claude-sonnet-5"  # tesis de entrada; ver docs/COSTOS.md
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"  # paper; live es deliberado
    execution_enabled: bool = False  # True => el ciclo diario EJECUTA (fase 4)


@lru_cache
def get_settings() -> Settings:
    return Settings()
