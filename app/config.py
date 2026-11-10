from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://larkfield:larkfield@localhost:5433/larkfield"

    llm_provider: str = "ollama"  # ollama | anthropic
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "fusion27b:iq3"
    embed_model: str = "nomic-embed-text"
    embed_dims: int = 768
    llm_timeout_s: float = 120.0

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    # USD per million tokens, used only for cost reporting. Set from the provider's price page.
    price_in_per_mtok: float = 0.0
    price_out_per_mtok: float = 0.0
    usd_to_inr: float = 88.0

    retrieval_k: int = 5
    max_tool_rounds: int = 4
    # Frozen "now" (ISO datetime) for reproducible evals: orders have fixed dates, so a real clock makes
    # return-window cases flip as the calendar moves. Unset in production.
    clock_now: str | None = None

    slack_bot_token: str | None = None
    slack_app_token: str | None = None

    allowed_codes: str = ""  # comma-separated discount codes the agent may mention


settings = Settings()
