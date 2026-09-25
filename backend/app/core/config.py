from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    FILES_DIR: str = "/data/files"
    LLM_PROVIDER: str = "fake"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = ""
    RETENTION_DAYS: int = 30
    MAX_UPLOAD_MB: int = 20
    NEO4J_URL: str = ""

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()
