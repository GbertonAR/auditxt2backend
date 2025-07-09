# backend/services/azure_transcriptor.py

from pathlib import Path
import logging
import azure.cognitiveservices.speech as speechsdk
import time
from pydub import AudioSegment

from Backend_app.config import settings

logger = logging.getLogger(__name__)

# --- Constantes ---
AZURE_KEY = settings.azure_speech_key
AZURE_REGION = settings.azure_region
LANGUAGE = "es-AR"

# --- Funciones utilitarias ---
def transcribir_azure_audio(path_audio: str) -> str:
    logger.info("🔍 Transcribiendo con Azure...")
    print("Azure Key:", AZURE_KEY)
    print("Azure Region:", AZURE_REGION)
    print("Language:", LANGUAGE)
    print("Audio Path:", path_audio)

    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    print(f"Configuración de Azure: {speech_config}")
    speech_config.speech_recognition_language = LANGUAGE
    audio_config = speechsdk.AudioConfig(filename=path_audio)
    
    print(f"Configuración de Azure: {speech_config}")
    print(f"Configuración de audio: {audio_config}")

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

# --- Función principal ---
async def transcribir_archivo_azure(upload_file) -> str:
    logger.info(f"📥 Archivo recibido para transcripción: {upload_file.filename}")

    # Asegurar que el directorio de trabajo exista
    WORK_DIR = settings.work_dir / "audio_work"
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    # Guardar el archivo con un nombre único
    original_ext = Path(upload_file.filename).suffix
    base_name = Path(upload_file.filename).stem
    original_path = WORK_DIR / f"{base_name}{original_ext}"

    with open(original_path, "wb") as f:
        contenido = await upload_file.read()
        f.write(contenido)

    logger.info(f"📁 Archivo guardado en: {original_path}")

    # Convertir el archivo MP3 a WAV
    wav_path = original_path.with_suffix(".wav")
    
    audio = AudioSegment.from_file(original_path)
    audio.export(wav_path, format="wav")

    # Transcribir el archivo de audio
    texto = transcribir_azure_audio(str(wav_path))
    logger.info(f"📝 Texto recibido: {texto!r}")

    if not texto:
        logger.warning("⚠️ No se reconoció ningún texto en el audio.")
        return ""

    return texto
