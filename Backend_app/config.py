# Backend_app/config.py

from pydantic-settings import BaseSettings, SettingsConfigDict
from pathlib import Path # Importa Path para manejar rutas de forma limpia

class Settings(BaseSettings):
    # Tus variables existentes (ej. Azure OpenAI)
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT: str
    API_VERSION: str

    # ASEGÚRATE DE QUE ESTAS LÍNEAS ESTÉN AQUÍ:
    AZURE_SPEECH_KEY: str  # Si no la tenías, añádela
    AZURE_REGION: str      # Si no la tenías, añádela
    work_dir: Path         # ¡Esta es la que faltaba!
    data_work: Path        # ¡Esta es la otra que faltaba!
    audio_work: Path        # ¡Y esta también!
    # Si también usas LANGUAGE en transcriptor.py desde settings, añádelo
    # language: str = "es-ES" # Con un valor por defecto si lo deseas

    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore' # Para ignorar variables en .env que no estén en la clase Settings
    )

# Crea la instancia de settings para que sea importable
settings = Settings()