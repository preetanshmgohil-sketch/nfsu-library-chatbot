"""Application settings for the NFSU Library Chatbot backend."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    app_name: str = "NFSU Library Chatbot"
    environment: str = "development"
    debug: bool = False

    # --- CORS / origin allowlist (KOHA OPAC and approved origins) ---
    allowed_origins: List[str] = [
        "https://catalog.nfsu.ac.in",
        "https://catalog.nfsu.ac.in:443",
        "http://localhost",
        "http://127.0.0.1",
    ]
    # Dev convenience: any localhost / 127.0.0.1 port, plus the OPAC domain tree.
    # Production can disable this by setting ALLOW_ORIGINS_REGEX="".
    allowed_origins_regex: str = (
        r"https://([a-z0-9-]+\.)*nfsu\.ac\.in|"
        r"http://(localhost|127\.0\.0\.1)(:\d+)?"
    )

    # --- KOHA (verified against live catalog.nfsu.ac.in) ---
    # Real OPAC paths: /cgi-bin/koha/opac-search.pl · /cgi-bin/koha/opac-detail.pl
    # Real indexes: '' (keyword) | ti | au | su | nb | ns | se | callnum
    koha_opac_base_url: str = "https://catalog.nfsu.ac.in"
    koha_rest_base_url: Optional[str] = None
    koha_rest_token: Optional[str] = None
    koha_default_results: int = 5
    koha_max_results: int = 10
    # Scrape the public OPAC results page for real bibliographic cards
    # (no credentials required). Disable to force deep-link-only mode.
    koha_scrape_enabled: bool = True
    koha_scrape_timeout_seconds: float = 20.0
    # Optional IP pin for environments where the hostname does not resolve
    # (sets Host: catalog.nfsu.ac.in while connecting to this IP).
    koha_pin_ip: Optional[str] = None

    # --- LLM (Hugging Face Inference Providers — OpenAI-compatible) ---
    # Recommended for this task: Qwen/Qwen2.5-7B-Instruct (quality)
    # or Qwen/Qwen2.5-3B-Instruct (fast). Alternatives: Llama-3.1-8B-Instruct.
    # Set LLM_API_TOKEN=hf_... and leave LLM_ENDPOINT_URL blank to use the
    # HF router (https://router.huggingface.co/v1/chat/completions).
    # Or point LLM_ENDPOINT_URL at a private HF endpoint or local Ollama.
    llm_endpoint_url: Optional[str] = None
    llm_api_token: Optional[str] = None
    llm_model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_timeout_seconds: float = 30.0
    llm_max_input_chars: int = 2000
    llm_max_tokens: int = 512
    llm_enabled: bool = True

    # --- Security ---
    max_user_message_chars: int = 2000
    max_history_messages: int = 12
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    block_prompt_injection: bool = True

    # --- Widget behaviour ---
    widget_enabled: bool = True
    widget_suspended: bool = False
    default_locale: str = "en"
    supported_locales: List[str] = ["en", "hi"]

    # --- Analytics (privacy-preserving: counts only, no message content) ---
    analytics_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
