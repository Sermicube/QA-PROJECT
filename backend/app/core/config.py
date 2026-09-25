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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RETENTION_DAYS: int = 30
    MAX_UPLOAD_MB: int = 20
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "copiloto1234"
    NEO4J_ENABLED: bool = True

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()
