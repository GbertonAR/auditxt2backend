### Transcripción de archivos de audio usando Azure Speech Service
### transcribir_archivo.py


import os
import tempfile
import uuid
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import azure.cognitiveservices.speech as speechsdk
import logging
import traceback
from Backend_app.config import settings
from services.azure_transcriptor import transcribir_archivo_azure

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
router = APIRouter()

# Asegúrate que existe carpeta para guardar audios
os.makedirs("audios", exist_ok=True)

@router.post("/transcribir-archivo")
async def transcribir_archivo(audio: UploadFile = File(...), modo_salida: str = Form("dialogo")):
    logger.info("Paso por aca entrada")
    try:
        # Guarda archivo original temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{audio.filename}") as temp_input:
            contents = await audio.read()
            temp_input.write(contents)
            input_path = temp_input.name

        # Log de claves (solo en desarrollo, ¡no en producción!)
        logger.info(f"speech key: {settings.azure_speech_key}")
        logger.info(f"speech region: {settings.azure_region}")

        # Configuración Azure Speech
        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_region
        )
        audio_config = speechsdk.AudioConfig(filename=input_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        result = recognizer.recognize_once()

        # Guardar copia del audio para histórico
        filename = f"{uuid.uuid4()}.wav"
        output_path = os.path.join("audios", filename)
        with open(output_path, "wb") as f:
            f.write(contents)

        # Limpiar archivo temporal
        os.remove(input_path)

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            texto = result.text.strip()
            if not texto:
                return JSONResponse(status_code=200, content={
                    "transcripcion": "",
                    "advertencia": "No se detectó voz en el audio."
                })
            return {
                "transcripcion": texto,
                "modo_salida": modo_salida
            }
        else:
            return JSONResponse(status_code=500, content={
                "error": f"No se reconoció ningún discurso. Razón: {result.reason}"
            })

    except Exception as e:
        logger.error(f"Error al transcribir: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "error": "Error interno en el servidor al transcribir."
        })