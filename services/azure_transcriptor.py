# backend/services/azure_transcriptor.py

from pathlib import Path
import os
import subprocess
import logging
import azure.cognitiveservices.speech as speechsdk
import time
import re
from uuid import uuid4


from Backend_app.config import settings
from .azure_format_text import limpiar_y_formatear_dialogo, resumen_tematico


logger = logging.getLogger(__name__)

# --- Constantes ---
AZURE_KEY = settings.azure_speech_key
AZURE_REGION = settings.azure_region
LANGUAGE = "es-ES"
WORK_DIR = settings.work_dir / "audio_work"
FFMPEG_EXE = settings.work_dir / "ffmpeg.exe"

# --- Funciones utilitarias ---
def transcribir_azure_wav(path_audio: str) -> str:
    logger.info("🔍 Transcribiendo con Azure...")
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    speech_config.speech_recognition_language = LANGUAGE
    audio_config = speechsdk.AudioConfig(filename=path_audio)

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    texto = []

    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logger.info(f"🗣 Reconocido: {evt.result.text}")
            texto.append(evt.result.text)
        else:
            logger.info(f"🛑 No se reconoció texto en este fragmento")

    recognizer.recognized.connect(on_recognized)

    done = False
    def stop_cb(evt):
        nonlocal done
        done = True

    recognizer.session_stopped.connect(stop_cb)
    recognizer.canceled.connect(stop_cb)
    recognizer.speech_end_detected.connect(stop_cb)

    recognizer.start_continuous_recognition()

    start_time = time.time()
    while not done and time.time() - start_time < 60:
        time.sleep(0.5)

    recognizer.stop_continuous_recognition()

    return " ".join(texto).strip()

def limpiar_y_formatear_dialogo(texto: str) -> str:
    frases = re.split(r'(?<=[.?!])\s*', texto)
    return "\n\n".join([f.strip() for f in frases if f.strip()])

def resumen_tematico_placeholder(texto: str) -> str:
    return f"Resumen temático (simulado):\n\n{texto[:300]}..."

# --- Función principal ---
async def transcribir_archivo_azure(upload_file, modo_salida: str = "dialogo") -> str:
    logger.info(f"📥 Archivo recibido para transcripción: {upload_file.filename}, modo: {modo_salida}")

    # Asegurar que el directorio de trabajo exista
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Guardar el archivo con un nombre único
    original_ext = Path(upload_file.filename).suffix
    base_name = Path(upload_file.filename).stem
    unique_id = uuid4().hex[:8]
    original_path = WORK_DIR / f"{base_name}_{unique_id}{original_ext}"

    with open(original_path, "wb") as f:
        contenido = await upload_file.read()
        f.write(contenido)

    logger.info(f"📁 Archivo guardado en: {original_path}")

    # Convertir a WAV
    output_wav_path = original_path.with_suffix(".wav").with_name(f"{original_path.stem}_converted.wav")
    command = [
        str(FFMPEG_EXE),
        "-y",
        "-i", str(original_path),
        "-ac", "1",
        "-ar", "16000",
        "-sample_fmt", "s16",
        str(output_wav_path)
    ]

    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"✅ Conversión a WAV completada: {output_wav_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error en conversión a WAV: {e.stderr}")
        return "Error en la conversión de audio."

    # Transcribir
    texto = transcribir_azure_wav(str(output_wav_path))
    logger.info(f"📝 Texto recibido: {texto!r}")

    if not texto:
        logger.warning("⚠️ No se reconoció ningún texto en el audio.")
        return ""

    if modo_salida == "dialogo":
            texto_final = limpiar_y_formatear_dialogo(texto)
    elif modo_salida == "resumen":
            texto_final = resumen_tematico(texto)
    else:
            texto_final = texto
            
    # if modo_salida == "dialogo":
    #     return limpiar_y_formatear_dialogo(texto)
    # elif modo_salida == "resumen":
    #     return resumen_tematico_placeholder(texto)
    # else:
    #print(f"texto transcrito: {texto}")

    return texto_final
