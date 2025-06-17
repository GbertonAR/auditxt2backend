# backend/services/azure_transcriptor.py

import os
import tempfile
from pathlib import Path
import subprocess
import logging
import azure.cognitiveservices.speech as speechsdk
import time
import re

from Backend_app.config import settings

logger = logging.getLogger(__name__)

# --- Constantes y configuración ---
AZURE_KEY = settings.azure_speech_key
AZURE_REGION = settings.azure_region
LANGUAGE = "es-ES"


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
            texto.append(evt.result.text)

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
    # En producción deberías usar HuggingFace o Azure OpenAI aquí
    return f"Resumen temático (simulado):\n\n{texto[:300]}..."

# --- Función principal exportada ---
async def transcribir_archivo_azure(upload_file, modo_salida: str = "dialogo") -> str:
    logger.info(f"📥 Archivo recibido para transcripción: {upload_file.filename}, modo: {modo_salida}")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        contenido = await upload_file.read()
        tmp.write(contenido)
        tmp_path = tmp.name

    try:
         # Convertir a WAV
        FFMPEG_EXE = settings.work_dir / "ffmpeg.exe"
        wav_path = Path(tmp_path).with_suffix(".wav")
        print(f"🔄 Convertiendo a WAV: {wav_path}")
        print(f"tmp_path: {Path(tmp_path)}")

            # Archivo de salida distinto para evitar sobrescritura
        output_wav_path = wav_path.with_name(wav_path.stem + "_converted.wav")
        print(f"🔄 Convertiendo a WAV: {output_wav_path}")
        command = [
                str(FFMPEG_EXE),
                "-y",
                "-i", str(tmp_path),
                "-ac", "1",
                "-ar", "16000",
                "-sample_fmt", "s16",
                str(output_wav_path)
         ]

        subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info("✅ Conversión a WAV completada")

        # En la función transcribir_archivo_azure
        texto = transcribir_azure_wav(str(output_wav_path))
        #texto = transcribir_azure_wav(wav_path)
        if not texto:
            return ""

        if modo_salida == "dialogo":
            return limpiar_y_formatear_dialogo(texto)
        elif modo_salida == "resumen":
            return resumen_tematico_placeholder(texto)
        else:
            return texto

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

