from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str
    
    # Database (Railway PostgreSQL)
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/proxydb"
    
    # AI Services (выберите один или несколько)
    GEMINI_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    GROK_API_KEY: Optional[str] = None
    
    # AI Settings
    AI_PROVIDER: str = "gemini"  # gemini, huggingface, cohere, grok
    AI_MODEL: str = "gemini-pro"  # модель по умолчанию
    
    # Proxy Settings
    PROXY_CHECK_TIMEOUT: int = 10
    PROXY_CHECK_BATCH_SIZE: int = 100
    PROXY_AUTO_CHECK_INTERVAL: int = 30  # минут
    
    # GeoIP
    GEOLITE2_DB_PATH: str = "GeoLite2-Country.mmdb"
    
    # Scheduler
    ENABLE_AUTO_CHECK: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
