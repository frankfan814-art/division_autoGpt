"""Configuration management for Creative AutoGPT"""

from typing import Optional, List
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-this-in-production"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/creative_autogpt.db"

    # Vector Database
    chroma_persist_directory: str = "./data/chroma"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM Configuration
    default_provider: str = "multi"  # multi, aliyun, deepseek, ark
    smart_routing: bool = True
    router_strategy: str = "hybrid"  # hybrid, ai_only, rule_only
    router_cache_ttl: int = 300

    # Default LLM parameters
    default_temperature: float = 0.7
    default_max_tokens: int = 4000
    llm_request_timeout: int = 3600  # 60 minutes for batch chapter generation (128K tokens)
    max_retries: int = 3

    # Aliyun (Qwen)
    aliyun_api_key: Optional[str] = None
    aliyun_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    aliyun_model: str = "qwen-long"
    aliyun_enabled: bool = True
    aliyun_embedding_model: str = "text-embedding-v3"
    aliyun_embedding_base_url: str = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding-v3"

    # DeepSeek
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_enabled: bool = True

    # Ark (Doubao)
    ark_api_key: Optional[str] = None
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ark_model: str = "ep-20250118094854-wd5pp"
    ark_enabled: bool = True

    # NVIDIA (optional backup)
    nvidia_api_key: Optional[str] = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1/chat/completions"
    nvidia_model: str = "deepseek-ai/DeepSeek-V3"
    nvidia_enabled: bool = False

    # Storage
    storage_type: str = "local"  # local, s3
    local_storage_path: str = "./data/novels"

    # Logging
    log_level: str = "DEBUG"
    log_file: str = "./logs/app.log"
    log_rotation: str = "1 day"
    log_retention: str = "30 days"

    # Performance
    max_concurrent_tasks: int = 5
    worker_pool_size: int = 10

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:4173",
    ]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in ("development", "dev")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")

    def get_data_dir(self) -> Path:
        """Get data directory path, creating if needed"""
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)
        return data_dir

    def get_logs_dir(self) -> Path:
        """Get logs directory path, creating if needed"""
        logs_dir = Path("./logs")
        logs_dir.mkdir(exist_ok=True)
        return logs_dir


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance, creating if needed"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset global settings instance (mainly for testing)"""
    global _settings
    _settings = None
