# backend/services/azure_core.py
import os
import azure.cognitiveservices.speech as speechsdk
from Backend_app.config import settings
import re
import logging

logger = logging.getLogger(__name__)

def transcribir_audio_azure_sdk(path_audio: str, modo_salida: str) -> str:
    logger.info(f"🎙️ Procesando: {path_audio}, modo: {modo_salida}")

    # Configurar Azure Speech
    speech_config = speechsdk.SpeechConfig(
        subscription=settings.azure_speech_key,
        region=settings.azure_region
    )
    speech_config.speech_recognition_language = "es-ES"  # Puedes parametrizar esto si lo necesitas
    audio_input = speechsdk.AudioConfig(filename=path_audio)

    # Crear el reconocedor
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_input
    )

    # Transcribir de una vez
    result = recognizer.recognize_once()

    logger.info(f"🔍 Resultado Azure: {result.reason}")
    logger.debug(f"Texto detectado: {result.text}")

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        texto = result.text.strip()
        if not texto:
            return ""

        if modo_salida == "dialogo":
            return formatear_como_dialogo(texto)
        else:
            return texto

    elif result.reason == speechsdk.ResultReason.NoMatch:
        logger.warning("⚠️ No se reconoció ninguna palabra.")
        return ""

    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        logger.error(f"❌ Cancelado por: {cancellation.reason}")
        if cancellation.reason == speechsdk.CancellationReason.Error:
            logger.error(f"🔎 Código: {cancellation.error_code}")
            logger.error(f"🧾 Detalles: {cancellation.error_details}")
        return ""

    else:
        logger.error("⚠️ Resultado inesperado.")
        return ""

def formatear_como_dialogo(texto: str) -> str:
    """Divide texto plano en frases tipo diálogo."""
    frases = re.split(r'(?<=[.?!])\s+', texto)
    return "\n\n".join(f"• {frase.strip()}" for frase in frases if frase.strip())
