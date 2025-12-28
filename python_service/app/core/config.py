"""
Application configuration settings
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # LLM Provider (openai, anthropic, or mock)
    LLM_PROVIDER: str = "openai"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"

    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"

    # Shopify
    SHOPIFY_API_VERSION: str = "2024-01"

    # Redis (for caching)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 minutes

    # Agent settings
    MAX_RETRIES: int = 3
    AGENT_TIMEOUT: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
