# Backend_app/routers/transcriptor_audio.py

import tempfile
import uuid
import logging
import traceback
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import azure.cognitiveservices.speech as speechsdk

from Backend_app.config import settings

# Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Crear carpeta de trabajo si no existe
settings.work_dir.mkdir(parents=True, exist_ok=True)

router = APIRouter()

@router.post("/transcribir-archivo")
async def transcribir_archivo(audio: UploadFile = File(...), modo_salida: str = Form("dialogo")):
    try:
        # Leer contenido del archivo
        contents = await audio.read()

        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{audio.filename}") as temp_input:
            temp_input.write(contents)
            input_path = temp_input.name
        print(f"Region de setteos: {settings.azure_region}")
        # Configurar Azure Speech SDK
        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_region
        )
        
        print(f"Configuración de Azure Speech SDK: {speech_config.subscription}, {speech_config.region}")
        audio_config = speechsdk.AudioConfig(filename=input_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        logger.info(f"Reconociendo archivo: {audio.filename}")
        result = recognizer.recognize_once()

        # Eliminar archivo temporal
        tempfile_path = Path(input_path)
        if tempfile_path.exists():
            tempfile_path.unlink()

        # Guardar una copia del audio subido
        output_filename = f"{uuid.uuid4()}.wav"
        output_path = settings.work_dir / output_filename
        with open(output_path, "wb") as f:
            f.write(contents)

        # Procesar resultado
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            texto = result.text.strip()
            if not texto:
                return JSONResponse(status_code=200, content={
                    "transcripcion": "",
                    "advertencia": "No se detectó voz en el audio."
                })
            return {
                "transcripcion": texto,
                "modo_salida": modo_salida,
                "archivo_guardado": output_filename
            }

        elif result.reason == speechsdk.ResultReason.NoMatch:
            return JSONResponse(status_code=400, content={"error": "No se reconoció ningún discurso en el archivo."})

        else:
            return JSONResponse(status_code=500, content={"error": f"Error inesperado: {result.reason}"})

    except Exception as e:
        logger.error(f"Error al transcribir: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "Error interno al transcribir el archivo."})
