import azure.cognitiveservices.speech as speechsdk
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")

def limpiar_transcripcion(texto):
    # Eliminación de repeticiones simples y limpieza básica
    import re
    palabras = texto.split()
    resultado = [palabras[0]] if palabras else []
    for palabra in palabras[1:]:
        if palabra != resultado[-1]:
            resultado.append(palabra)
    texto_limpio = ' '.join(resultado)
    return re.sub(r'\s+', ' ', texto_limpio).strip()

async def transcribir_audio_azure_sdk(audio_file, modo_salida="simple"):
    if not AZURE_SPEECH_KEY or not AZURE_REGION:
        return "Error: Falta configuración de Azure Speech."

    # Guardar el archivo de audio temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        contents = await audio_file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Configurar cliente de Azure Speech
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
        speech_config.speech_recognition_language = "es-ES"

        audio_config = speechsdk.audio.AudioConfig(filename=tmp_path)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        done = False
        transcripcion = []

        def handle_result(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcripcion.append(evt.result.text)

        recognizer.recognized.connect(handle_result)

        def stop_cb(evt):
            nonlocal done
            done = True

        recognizer.session_stopped.connect(stop_cb)
        recognizer.canceled.connect(stop_cb)

        recognizer.start_continuous_recognition()
        while not done:
            await asyncio.sleep(0.5)
        recognizer.stop_continuous_recognition()

        texto_final = " ".join(transcripcion)

        if not texto_final.strip():
            return "Transcripción vacía. ¿Audio demasiado corto o sin voz?"

        texto_limpio = limpiar_transcripcion(texto_final)
        return texto_limpio if modo_salida == "simple" else f"[DIÁLOGO]\n{texto_limpio}"

    finally:
        os.unlink(tmp_path)  # Eliminar archivo temporal
