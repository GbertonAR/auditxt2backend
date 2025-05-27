import os
import subprocess
import wave
import contextlib

import json
import soundfile as sf
import subprocess
from azure.cognitiveservices.speech import SpeechConfig, AudioConfig, SpeechRecognizer
import azure.cognitiveservices.speech as speechsdk

def verificar_archivo_wav(ruta):
    print("🔍 Verificando archivo WAV...")
    if not os.path.exists(ruta):
        print(f"❌ Archivo no encontrado: {ruta}")
        return False
    try:
        with contextlib.closing(wave.open(ruta, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duracion = frames / float(rate)
            print(f"✅ Archivo válido. Duración: {duracion:.2f} segundos")
            return duracion > 0
    except wave.Error as e:
        print(f"❌ Error al leer el WAV: {e}")
        return False

def reproducir_audio(ruta):
    print("🔊 Reproduciendo audio (ffplay)...")
    try:
        subprocess.run(["ffplay", "-nodisp", "-autoexit", ruta], check=True)
    except Exception as e:
        print(f"⚠️ Error al reproducir el audio: {e}")

def test_azure_transcripcion(ruta_wav, speech_key, region, language="es-ES"):
    print("🧠 Probando transcripción con Azure...")
    try:
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=region)
        speech_config.speech_recognition_language = language
        speech_config.output_format = speechsdk.OutputFormat.Detailed

        audio_input = speechsdk.audio.AudioConfig(filename=ruta_wav)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

        done = False
        resultado_final = []

        def recognized(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                result_json = json.loads(evt.result.json)
                for nbest in result_json.get("NBest", []):
                    texto = nbest.get("Display", "")
                    print(f"📝 Azure reconoció: {texto}")
                    resultado_final.append(texto)

        def canceled(evt):
            print(f"❌ Transcripción cancelada: {evt.reason}")
            if evt.reason == speechsdk.CancellationReason.Error:
                print(f"Detalles del error: {evt.error_details}")

        def session_stopped(evt):
            nonlocal done
            print("✅ Sesión de transcripción finalizada.")
            done = True

        recognizer.recognized.connect(recognized)
        recognizer.canceled.connect(canceled)
        recognizer.session_stopped.connect(session_stopped)

        recognizer.start_continuous_recognition()
        while not done:
            pass
        recognizer.stop_continuous_recognition()

        if not resultado_final:
            print("⚠️ No se obtuvo texto de Azure.")
        else:
            print(f"✅ {len(resultado_final)} segmentos reconocidos correctamente.")
        return resultado_final

    except Exception as e:
        print(f"❌ Error durante la prueba con Azure: {e}")
        return []


def diagnostico_completo(ruta_wav, azure_key, azure_region):
    from azure.cognitiveservices.speech import SpeechConfig, AudioConfig, SpeechRecognizer, ResultReason
    import os
    import subprocess

    print("\n🔧 Iniciando diagnóstico completo...")

    # Verificación básica
    print("🔍 Verificando archivo WAV...")
    if not os.path.exists(ruta_wav):
        print("❌ Archivo no encontrado.")
        return

    try:
        data, samplerate = sf.read(ruta_wav)
        duracion = len(data) / samplerate
        print(f"✅ Archivo válido. Duración: {duracion:.2f} segundos")
    except Exception as e:
        print(f"❌ Error al leer el archivo: {e}")
        return

    # Reproducción opcional
    print("🔊 Reproduciendo audio (ffplay)...")
    try:
        subprocess.run(["ffplay", "-autoexit", "-nodisp", ruta_wav])
    except FileNotFoundError:
        print("⚠️ ffplay no está instalado. Omitiendo reproducción.")

    # Transcripción básica solo primeros 60 segundos
    print("🧪 Probando transcripción básica con Azure...")

    try:
        speech_config = SpeechConfig(subscription=azure_key, region=azure_region)
        audio_config = AudioConfig(filename=ruta_wav)

        # Reconocedor
        speech_recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        result = speech_recognizer.recognize_once()
        if result.reason == ResultReason.RecognizedSpeech:
            print("✅ Azure reconoció texto:")
            print(result.text)
        elif result.reason == ResultReason.NoMatch:
            print("❌ Azure no detectó voz reconocible.")
        elif result.reason == ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print(f"❌ Error en reconocimiento: {result.reason}")
            print(f"   Motivo: {cancellation_details.reason}")
            if cancellation_details.error_details:
                print(f"   Detalles: {cancellation_details.error_details}")
    except Exception as e:
        print(f"❌ Error al conectar con Azure: {e}")
