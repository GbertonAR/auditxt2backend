from pathlib import Path
import os
import subprocess
import logging
import azure.cognitiveservices.speech as speechsdk
import time
import re
import wave
from uuid import uuid4

from Backend_app.config import settings
from .azure_format_text import limpiar_y_formatear_dialogo, resumen_tematico

logger = logging.getLogger(__name__)

# --- Constantes ---
AZURE_KEY = settings.azure_speech_key
#AZURE_REGION = settings.azure_region
AZURE_REGION = settings.azure_speech_region  # Cambiado para usar la variable de entorno
LANGUAGE = "es-ES"  # Usa es-ES o es-MX para mayor compatibilidad
#WORK_DIR = settings.work_dir / "audio_work"
WORK_DIR = Path("C:/tmp/auditxt")

FFMPEG_EXE = settings.work_dir / "ffmpeg.exe"

# --- Transcripción con Azure ---
def transcribir_azure_wav(path_audio: str) -> str:
    logger.info("🔍 Transcribiendo con Azure...")
    print("Azure Key:", AZURE_KEY)
    print("Azure Region:", AZURE_REGION)
    print("Language:", LANGUAGE)
    print("Audio Path:", path_audio)

    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    speech_config.speech_recognition_language = LANGUAGE
    audio_config = speechsdk.AudioConfig(filename=path_audio)

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    texto = []

    def on_session_started(evt):
        logger.info("✅ Sesión de reconocimiento iniciada.")

    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logger.info(f"🗣 Reconocido: {evt.result.text}")
            texto.append(evt.result.text)
        else:
            logger.info(f"🛑 No se reconoció texto en este fragmento")

    def on_canceled(evt):
        logger.error(f"🚫 Transcripción cancelada: {evt.reason}, error_details: {evt.error_details}")

    def stop_cb(evt):
        nonlocal done
        done = True

    recognizer.session_started.connect(on_session_started)
    recognizer.recognized.connect(on_recognized)
    recognizer.canceled.connect(on_canceled)
    recognizer.session_stopped.connect(stop_cb)
    recognizer.speech_end_detected.connect(stop_cb)

    done = False
    recognizer.start_continuous_recognition()

    start_time = time.time()
    while not done and time.time() - start_time < 60:
        time.sleep(0.5)

    recognizer.stop_continuous_recognition()

    return " ".join(texto).strip()

# --- Texto enriquecido ---
def limpiar_y_formatear_dialogo(texto: str) -> str:
    frases = re.split(r'(?<=[.?!])\s*', texto)
    return "\n\n".join([f.strip() for f in frases if f.strip()])

def resumen_tematico_placeholder(texto: str) -> str:
    return f"Resumen temático (simulado):\n\n{texto[:300]}..."

# --- Función principal ---
async def transcribir_archivo_azure(upload_file, modo_salida: str = "dialogo") -> str:
    logger.info(f"📥 Archivo recibido para transcripción: {upload_file.filename}, modo: {modo_salida}")

    # Asegurar carpeta de trabajo
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Guardar el archivo
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

    # Leer duración para debug
    try:
        with wave.open(str(output_wav_path), "rb") as wf:
            duration = wf.getnframes() / wf.getframerate()
            logger.info(f"🔍 Duración del audio: {duration:.2f} segundos")
    except Exception as e:
        logger.warning(f"⚠️ Error leyendo el WAV antes de transcribir: {e}")

    # Transcripción
    try:
        texto = transcribir_azure_wav(str(output_wav_path))
        logger.info(f"📝 Texto recibido: {texto!r}")
    except Exception as e:
        logger.exception("❌ Error inesperado durante transcripción")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

    if not texto:
        logger.warning("⚠️ No se reconoció ningún texto en el audio.")
        return ""

    # Procesamiento adicional
    if modo_salida == "dialogo":
        return limpiar_y_formatear_dialogo(texto)
    elif modo_salida == "resumen":
        return resumen_tematico(texto)
    else:
        return texto
