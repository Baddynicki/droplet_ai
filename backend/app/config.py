from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://root:1234@localhost:5432/ide_db"
    openrouter_api_key: str = ""
    openrouter_model: str = "poolside/laguna-s-2.1:free"
    paper_storage_dir: Path = Path("storage/papers")
    max_pdf_size_mb: int = 25
    max_papers_per_job: int = 3
    max_paper_text_chars: int = 90_000

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
settings.paper_storage_dir.mkdir(parents=True, exist_ok=True)