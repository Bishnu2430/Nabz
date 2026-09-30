from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "info"
    database_url: str = "postgresql+psycopg://nabz:nabz@localhost:5433/nabz"
    upload_dir: str = "/data/uploads"
    data_dir: str = "/srv/data"

    # Accounts (docs/12 §3). SECRET_KEY encrypts TOTP secrets; it must be set outside development.
    secret_key: str = "development-only-secret-change-me"  # noqa: S105 - refused outside development (main.py)
    app_base_url: str = "http://localhost:5173"  # links in emails
    session_idle_days: int = 14
    staff_session_hours: int = 24
    cookie_secure: bool = False  # True behind HTTPS
    mail_backend: str = "smtp"  # smtp | memory (tests)
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    mail_from: str = "Nabz <no-reply@nabz.local>"

    # Explanations and safety judge (ADR-0007). gpt-oss-120b is text-only, so the
    # consent-gated photo fallback uses a separate vision model.
    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_api_key: str = ""
    # gpt-oss reasoning effort for the explanation writer; reasoning tokens count against the rate limit.
    llm_reasoning_effort: str = "low"
    local_llm_base_url: str = "http://ollama:11434"
    local_llm_model: str = "qwen3:4b"

    # Narration (ADR-0008).
    tts_provider: str = "elevenlabs"
    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    # eleven_multilingual_v2 has no Odia; eleven_v4 does (checked with GET /v1/models, 2026-09-30).
    elevenlabs_model_or: str = "eleven_v4"
    elevenlabs_voice_en: str = ""
    elevenlabs_voice_hi: str = ""
    elevenlabs_voice_or: str = ""


settings = Settings()
