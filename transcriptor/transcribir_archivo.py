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
    try:
        logger.info("📥 Archivo recibido para transcripción")
        logger.info(f"Nombre del archivo: {audio.filename}")
        logger.info(f"Tamaño del archivo: {audio.size} bytes")
        # Validar tipo de archivo
        if not audio.filename.lower().endswith(('.wav', '.mp3', '.flac', '.ogg', '.m4a')):
            logger.error("❌ Tipo de archivo no soportado")
            return JSONResponse(status_code=400, content={
                "error": "Tipo de archivo no soportado. Solo se permiten archivos de audio."
            })
        print(f"modo_salida: {modo_salida}")
        #texto = await transcribir_archivo_azure(audio, modo_salida)
        texto = await transcribir_archivo_azure(audio)

        print(f"Texto transcrito (transcribir_archivo.py): {texto}")
        if not texto.strip():
            return JSONResponse(status_code=200, content={
                "transcripcion": "",
                "advertencia": "No se detectó voz en el audio."
            })

        return {"transcripcion": texto.strip(), "modo_salida": modo_salida}

    except Exception as e:
        logger.error(f"❌ Error al transcribir: {e}")
        return JSONResponse(status_code=500, content={
            "error": "Error interno en el servidor al transcribir."
        })