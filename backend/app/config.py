"""Configuration management for QuantaBench backend."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    env: str = Field(default="development", description="Environment name")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_reload: bool = Field(default=True, description="Enable auto-reload")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated CORS origins",
    )

    # Classiq Authentication
    classiq_client_id: str = Field(default="", description="Classiq M2M client ID")
    classiq_client_secret: str = Field(default="", description="Classiq M2M secret")

    # qBraid Authentication
    qbraid_api_key: str = Field(default="", description="qBraid API key")

    # IonQ (self-managed)
    ionq_api_key: str = Field(default="", description="IonQ API key")

    # Feature Flags
    enable_classiq: bool = Field(default=True, description="Enable Classiq backend")
    enable_qbraid: bool = Field(default=True, description="Enable qBraid backend")
    enable_hardware: bool = Field(
        default=False, description="Enable hardware execution"
    )
    cache_enabled: bool = Field(default=True, description="Enable result caching")

    # Optimization Settings
    default_qaoa_p: int = Field(default=2, description="Default QAOA layers")
    max_qaoa_p: int = Field(default=3, description="Maximum QAOA layers")
    default_shots: int = Field(default=1024, description="Default shots per execution")
    max_optimizer_restarts: int = Field(
        default=3, description="Max COBYLA restarts"
    )

    # Cache Settings
    cache_dir: str = Field(default=".cache", description="Cache directory")
    cache_ttl_hours: int = Field(default=168, description="Cache TTL in hours")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def cache_path(self) -> Path:
        """Get cache directory path."""
        return Path(self.cache_dir)

    def is_classiq_configured(self) -> bool:
        """Check if Classiq credentials are configured."""
        return bool(self.classiq_client_id and self.classiq_client_secret)

    def is_qbraid_configured(self) -> bool:
        """Check if qBraid is configured."""
        return bool(self.qbraid_api_key)

    def is_ionq_configured(self) -> bool:
        """Check if IonQ is configured."""
        return bool(self.ionq_api_key)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
