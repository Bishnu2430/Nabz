from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "info"
    database_url: str = "postgresql+psycopg://nabz:nabz@localhost:5433/nabz"
    upload_dir: str = "/data/uploads"

    llm_provider: str = "anthropic"
    llm_model: str = "claude-opus-5"
    local_llm_base_url: str = "http://ollama:11434"
    local_llm_model: str = "qwen3:4b"


settings = Settings()
