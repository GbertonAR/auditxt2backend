# API que transcribe audios transcription.py

import os
import subprocess
import azure.cognitiveservices.speech as speechsdk
import re
import time
from difflib import SequenceMatcher
from transformers import pipeline
from fastapi import FastAPI, Query
from pydantic import BaseModel
from diagnostico_audio import diagnostico_completo
import uvicorn

# Configuración
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "tu_clave")
AZURE_REGION = "westus"
LANGUAGE = "es-ES"

AUDIO_FILENAME = "output_audio.mp3"
WAV_FILENAME = "output_audio.wav"

app = FastAPI(title="API de Transcripción desde YouTube", description="Convierte videos a texto usando Azure y FastAPI.")

# Utilidades
def validar_url_youtube(url: str) -> bool:
    """Valida si la URL es accesible para yt-dlp (no descargamos aún)."""
    result = subprocess.run(["yt-dlp", "--simulate", url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0

def download_audio(url, output_file):
    print("📥 Descargando audio de YouTube...")
    result = subprocess.run([
        "yt-dlp", "-x", "--audio-format", "mp3", "-o", output_file, url
    ])
    if result.returncode != 0:
        raise Exception("❌ Error al descargar audio con yt-dlp.")
    print("✅ Audio descargado correctamente.")

def convert_mp3_to_wav(mp3_file, wav_file):
    print("🔄 Convirtiendo MP3 a WAV...")
    command = [
        "ffmpeg", "-y", "-i", mp3_file,
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", wav_file
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise Exception("❌ Error al convertir MP3 a WAV.")
    print("✅ Conversión completada.")

def transcribe_audio_detailed(ruta_wav, azure_key, azure_region, language="es-ES"):
    speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
    speech_config.speech_recognition_language = language
    audio_input = speechsdk.AudioConfig(filename=ruta_wav)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    transcripcion_completa = []

    def handle_final_result(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            transcripcion_completa.append(evt.result.text)
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print("⚠️ No se reconoció voz en un fragmento.")

    done = False
    def stop_cb(evt):
        nonlocal done
        done = True

    speech_recognizer.recognized.connect(handle_final_result)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    print("▶️ Iniciando transcripción...")
    speech_recognizer.start_continuous_recognition()

    while not done:
        time.sleep(0.5)

    speech_recognizer.stop_continuous_recognition()
    texto_final = " ".join(transcripcion_completa)
    return texto_final

def limpiar_y_formatear_dialogo(texto: str) -> str:
    dialogo = []
    for linea in texto.splitlines():
        if ":" in linea:
            orador, contenido = linea.split(":", 1)
            frases = re.split(r'(?<=[.?!])\s+', contenido.strip())
            for frase in frases:
                if frase:
                    dialogo.append(f"{orador.strip()}: {frase.strip()}")
    return "\n".join(dialogo)

def resumen_tematico(texto: str) -> str:
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    chunks = [texto[i:i+1024] for i in range(0, len(texto), 1024)]
    resumenes = summarizer(chunks, max_length=300, min_length=100, do_sample=False)
    return "\n\n".join([r['summary_text'] for r in resumenes])

def generar_documento_presentacion(texto_dialogo: str, archivo="transcripcion_presentable.txt"):
    contenido = f"TRANSCRIPCIÓN LIMPIA\n\n{texto_dialogo}"
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"📄 Documento generado: {archivo}")

def procesar_link(link: str, modo_salida: str = "dialogo") -> str:
    try:
        if not validar_url_youtube(link):
            raise Exception("URL no válida o inaccesible por yt-dlp.")

        download_audio(link, AUDIO_FILENAME)
        convert_mp3_to_wav(AUDIO_FILENAME, WAV_FILENAME)

        #diagnostico_completo(WAV_FILENAME, AZURE_SPEECH_KEY, AZURE_REGION)

        texto_crudo = transcribe_audio_detailed(WAV_FILENAME, AZURE_SPEECH_KEY, AZURE_REGION, LANGUAGE)

        if not texto_crudo.strip():
            return "⚠️ No se obtuvo texto del audio."

        if modo_salida == "dialogo":
            dialogo = limpiar_y_formatear_dialogo(texto_crudo)
            generar_documento_presentacion(dialogo)
            return dialogo

        elif modo_salida == "resumen":
            return resumen_tematico(texto_crudo)

        else:
            return "❌ Modo inválido. Usa 'dialogo' o 'resumen'."

    except Exception as e:
        return f"❌ Error: {str(e)}"

    finally:
        # Limpieza de archivos temporales
        for archivo in [AUDIO_FILENAME, WAV_FILENAME]:
            try:
                if os.path.exists(archivo):
                    os.remove(archivo)
                    print(f"🗑️ Archivo eliminado: {archivo}")
            except Exception as cleanup_err:
                print(f"⚠️ Error al eliminar {archivo}: {cleanup_err}")

# Interfaz FastAPI
class LinkRequest(BaseModel):
    link: str
    modo_salida: str = "dialogo"

@app.post("/transcribir/")
def transcribir_audio(data: LinkRequest):
    resultado = procesar_link(data.link, data.modo_salida)
    return {"resultado": resultado}

@app.get("/transcribir/")
def transcribir_get(link: str = Query(...), modo_salida: str = Query("dialogo")):
    resultado = procesar_link(link, modo_salida)
    return {"resultado": resultado}

# Ejecutar con uvicorn: `uvicorn main:app --reload`
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
