"""
Configuration Management

Centralized configuration using Pydantic Settings for environment variables.
"""

from typing import Optional, List, Union, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    PROJECT_NAME: str = "ECOWAS Summit TWG Support System"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./ecowas_db.sqlite",
        description="Database connection string"
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
        default=300,
        description="LLM request timeout in seconds"
    )
    
    # OpenAI (from Auth implementation)
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"

    # Message Bus Settings
    MESSAGE_BUS_ENABLED: bool = Field(
        default=True,
        description="Enable Redis message bus for agent communication"
    )
    MESSAGE_BUS_MAX_QUEUE_SIZE: int = Field(
        default=1000,
        description="Maximum messages per agent queue"
    )
    MESSAGE_BUS_DEFAULT_TIMEOUT: int = Field(
        default=30,
        description="Default timeout for blocking operations (seconds)"
    )
    MESSAGE_BUS_MESSAGE_TTL: int = Field(
        default=3600,
        description="Message TTL in seconds (1 hour)"
    )

    # Enhanced Routing Settings
    AGENT_USE_ENHANCED_ROUTING: bool = Field(
        default=False,
        description="Use enhanced confidence-based routing (feature flag)"
    )
    ROUTING_CONFIDENCE_THRESHOLD: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to select an agent"
    )
    ROUTING_MULTI_AGENT_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for multi-agent consultation"
    )
    ROUTING_MAX_PARALLEL_AGENTS: int = Field(
        default=3,
        ge=1,
        le=6,
        description="Maximum agents to consult in parallel"
    )

    # Peer Delegation Settings
    AGENT_PEER_DELEGATION_ENABLED: bool = Field(
        default=False,
        description="Allow agents to delegate to peers (feature flag)"
    )
    AGENT_MAX_DELEGATION_DEPTH: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum delegation chain depth"
    )
    AGENT_RESPONSE_TIMEOUT: int = Field(
        default=30,
        description="Timeout for agent responses (seconds)"
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
    JWT_SECRET_KEY: Optional[str] = None # For compatibility
    JWT_ALGORITHM: str = "HS256"
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm") # For compatibility
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration in days"
    )
    
    # Password Policy
    PASSWORD_MIN_LENGTH: int = 8
    REQUIRE_SPECIAL_CHAR: bool = True

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # PINECONE
    PINECONE_API_KEY: str = Field(default="test-key", description="Pinecone API key")
    PINECONE_ENVIRONMENT: str = Field(default="gcp-starter", description="Pinecone environment")
    PINECONE_INDEX_NAME: str = Field(default="martin-index", description="Pinecone index name")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Embedding model name")
    EMBEDDING_DIMENSION: int = Field(default=1536, description="Embedding dimension")
    
    # Email
    SMTP_SERVER: str = Field(default="localhost", description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    EMAILS_FROM_EMAIL: str = Field(default="martin@ecowas-summit.org", description="Sender email address")
    EMAILS_FROM_NAME: str = Field(default="Martin (ECOWAS Summit)", description="Sender name")
    EMAILS_ENABLED: bool = Field(default=True, description="Whether emails are enabled")
    SMTP_TLS: bool = Field(default=True, description="Whether to use TLS for SMTP")

    # Document Processing
    CHUNK_SIZE: int = Field(default=500, description="Document chunk size")
    CHUNK_OVERLAP: int = Field(default=50, description="Document chunk overlap")
    MAX_CHUNKS_PER_DOC: int = Field(default=1000, description="Maximum chunks per document")
    
    @property
    def cors_origins_list(self) -> list:
        """Parse CORS_ORIGINS string into a list"""
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Email Settings (for future use)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None

    # Gmail API Configuration
    GMAIL_CREDENTIALS_FILE: str = Field(
        default="./credentials/gmail_credentials.json",
        description="Path to Gmail OAuth credentials file"
    )
    GMAIL_TOKEN_FILE: str = Field(
        default="./credentials/gmail_token.json",
        description="Path to Gmail token file"
    )
    GMAIL_SCOPES: List[str] = Field(
        default=["https://mail.google.com/"],
        description="Gmail API scopes"
    )

    # Email Templates
    EMAIL_TEMPLATES_DIR: str = Field(
        default="./app/templates/email",
        description="Directory for email templates"
    )
    DEFAULT_EMAIL_FROM: Optional[str] = Field(
        default=None,
        description="Default sender email address"
    )

    # Storage
    UPLOAD_DIR: str = Field(
        default="./uploads",
        description="Directory for file uploads"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=10485760,  # 10MB
        description="Maximum upload size in bytes"
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


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

settings = get_settings()
