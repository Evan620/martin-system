"""
Configuration Management

Centralized configuration using Pydantic Settings for environment variables.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "ECOWAS Summit TWG Support System"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost:5432/ecowas_db",
        description="PostgreSQL connection string"
    )

    # Redis
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (overrides individual settings)"
    )
    REDIS_HOST: str = Field(default="localhost", description="Redis server host")
    REDIS_PORT: int = Field(default=6379, description="Redis server port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_MAX_CONNECTIONS: int = Field(default=10, description="Redis max connections")
    REDIS_MEMORY_TTL: int = Field(
        default=86400,
        description="Default TTL for Redis keys in seconds (24 hours)"
    )

    # LLM Settings
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    OLLAMA_MODEL: str = Field(
        default="qwen2.5:0.5b",
        description="Ollama model name"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.7,
        description="LLM sampling temperature"
    )
    LLM_TIMEOUT: int = Field(
        default=30,
        description="LLM request timeout in seconds"
    )

    # Agent Settings
    AGENT_USE_REDIS_MEMORY: bool = Field(
        default=True,
        description="Use Redis for agent memory persistence"
    )
    AGENT_MAX_HISTORY: int = Field(
        default=10,
        description="Maximum conversation history length"
    )
    SUPERVISOR_MAX_HISTORY: int = Field(
        default=20,
        description="Maximum conversation history for supervisor"
    )

    # Authentication
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="JWT secret key"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time"
    )

    # CORS
    CORS_ORIGINS: list = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins"
    )

    # Email Settings (for future use)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None

    # Storage
    UPLOAD_DIR: str = Field(
        default="./uploads",
        description="Directory for file uploads"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=10485760,  # 10MB
        description="Maximum upload size in bytes"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the settings singleton.

    Returns:
        Settings: Application settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
