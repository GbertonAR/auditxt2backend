# Backend_app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path # Importa Path para manejar rutas de forma limpia

class Settings(BaseSettings):
    # Tus variables existentes (ej. Azure OpenAI)
    azure_openai_key: str
    azure_openai_endpoint: str
    azure_openai_deployment: str
    api_version: str

    # ASEGÚRATE DE QUE ESTAS LÍNEAS ESTÉN AQUÍ:
    azure_speech_key: str  # Si no la tenías, añádela
    azure_region: str      # Si no la tenías, añádela
    work_dir: Path         # ¡Esta es la que faltaba!
    data_work: Path        # ¡Esta es la otra que faltaba!
    # Si también usas LANGUAGE en transcriptor.py desde settings, añádelo
    # language: str = "es-ES" # Con un valor por defecto si lo deseas

    model_config = SettingsConfigDict(
        env_file=".env",
        extra='ignore' # Para ignorar variables en .env que no estén en la clase Settings
    )

# Crea la instancia de settings para que sea importable
settings = Settings()