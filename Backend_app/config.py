from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field(..., env="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field("2025-03-01-preview", env="AZURE_OPENAI_API_VERSION")

    azure_speech_key: str = Field(..., env="AZURE_SPEECH_KEY")
    azure_region: str = Field(..., env="AZURE_REGION")

    port: int = Field(8000, env="PORT")
    build_during_deploy: bool = Field(False, env="SCM_DO_BUILD_DURING_DEPLOYMENT")

    # work_dir: str = Field(..., env="WORK_DIR")
    # data_work: str = Field(..., env="DATA_WORK")
    # audio_work: str = Field(..., env="AUDIO_WORK")
    
    work_dir: Path
    data_work: Path
    audio_work: Path

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()