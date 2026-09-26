from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "info"
    database_url: str = "postgresql+psycopg://nabz:nabz@localhost:5433/nabz"
    upload_dir: str = "/data/uploads"
    data_dir: str = "/srv/data"

    # Explanations and safety judge (ADR-0007). gpt-oss-120b is text-only, so the
    # consent-gated photo fallback uses a separate vision model.
    llm_provider: str = "groq"
    llm_model: str = "openai/gpt-oss-120b"
    vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_api_key: str = ""
    local_llm_base_url: str = "http://ollama:11434"
    local_llm_model: str = "qwen3:4b"

    # Narration (ADR-0008).
    tts_provider: str = "elevenlabs"
    elevenlabs_api_key: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    elevenlabs_voice_en: str = ""
    elevenlabs_voice_hi: str = ""
    elevenlabs_voice_or: str = ""


settings = Settings()
