# Backend_app/config.py
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    azure_openai_key: str = Field(..., env="AZURE_OPENAI_KEY")
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field(..., env="AZURE_OPENAI_DEPLOYMENT")
    api_version: str = Field("2025-03-01-preview", env="API_VERSION")  # O AZURE_OPENAI_API_VERSION si preferís

    audio_work: str = Field("/tmp/workdir/audio", env="audio_work")
    data_work: str = Field("/tmp/workdir/data", env="data_work")
    work_dir: str = Field("/tmp/workdir", env="work_dir")

    class Config:
        env_file = ".env"  # para desarrollo local (opcional)

settings = Settings()
