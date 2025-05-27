### Transcriptor de Audio a Texto para Web Auditxt2
# Este módulo maneja la transcripción de audio desde YouTube a texto
from dotenv import load_dotenv
import os
import subprocess
import re
import traceback # Importar traceback
import time
import azure.cognitiveservices.speech as speechsdk
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, HttpUrl
from typing import Optional
from transformers import pipeline
from utils.diagnostico_audio import diagnostico_completo
from Backend_app.config import settings
from pathlib import Path
# Carga las variables de entorno del archivo .env
load_dotenv()

router = APIRouter()

router = APIRouter(prefix="/api") # Asegúrate de este prefijo

AUDIO_FILENAME = "output_audio.mp3"
WAV_FILENAME = "output_audio.wav"
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_REGION = os.getenv("AZURE_REGION", "")
LANGUAGE = "es-ES"

# Rutas base desde settings
WORK_DIR = settings.work_dir
DATA_WORK = settings.data_work

# Asegurarse de que los directorios existan
os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(DATA_WORK, exist_ok=True)

# Rutas a los ejecutables (ahora en WORK_DIR)
YT_DLP_EXE = WORK_DIR / "yt-dlp.exe"
FFMPEG_EXE = WORK_DIR / "ffmpeg.exe"
FFPROBE_EXE = WORK_DIR / "ffprobe.exe"

# Rutas a los archivos de datos (ahora en DATA_WORK)
AUDIO_FILENAME = DATA_WORK / "audio_descargado.mp3"
WAV_FILENAME = DATA_WORK / "audio_convertido.wav"

# @router.post("/api/transcribir")
# async def transcribir(request: Request):
#     try:
#         # Aquí tu lógica para transcribir
#         return {"message": "Transcripción OK"}
#     except Exception as e:
#         # Imprime el error en consola para depurar
#         print("Error en /api/transcribir:", e)
#         raise HTTPException(status_code=500, detail=str(e))

class TranscripcionRequest(BaseModel):
    link: HttpUrl
    modo_salida: str = Query("dialogo", pattern="^(dialogo|resumen)$")

def validar_url_youtube(url: str) -> bool:
    return url.startswith("https://www.youtube.com/") or "youtu.be" in url

def download_audio(url: str, output_file: str):
    print("📥 Descargando audio de YouTube...")
    ffmpeg_path = r"C:\FFmpeg\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe" # Reemplaza con tu ruta real
    #yt_dlp_path = r"C:\donde\este\yt-dlp.exe" # Reemplaza con la ruta real a yt-dlp
    result = subprocess.run([
        "yt_dlp", "-x", "--audio-format", "mp3", "-o", output_file, url,
        "--ffmpeg-location", ffmpeg_path
    ], capture_output=True)    
    # result = subprocess.run([
    #     "yt-dlp", "-x", "--audio-format", "mp3", "-o", output_file, url
    # ], capture_output=True)
    if result.returncode != 0:
        print(result.stderr.decode())
        raise Exception("❌ Error al descargar audio con yt-dlp.")
    print("✅ Audio descargado correctamente.")

def convert_mp3_to_wav(mp3_file: str, wav_file: str):
    print("🎵 Convirtiendo MP3 a WAV...")
    command = [
        "ffmpeg", "-y", "-i", mp3_file,
        "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", wav_file
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(result.stderr.decode())
        raise Exception("❌ Error al convertir MP3 a WAV.")
    print("✅ Conversión completada.")

def transcribe_audio_detailed(ruta_wav: str, azure_key: str, azure_region: str, language: str = "es-ES") -> str:
    speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
    speech_config.speech_recognition_language = language
    audio_input = speechsdk.AudioConfig(filename=ruta_wav)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    texto = []

    def handle_final_result(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            texto.append(evt.result.text)

    recognizer.recognized.connect(handle_final_result)

    done = False
    def stop_cb(evt): nonlocal done; done = True
    recognizer.session_stopped.connect(stop_cb)
    recognizer.canceled.connect(stop_cb)

    recognizer.start_continuous_recognition()
    while not done:
        time.sleep(0.5)
    recognizer.stop_continuous_recognition()

    return " ".join(texto)

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

# Inicializar una sola vez el modelo summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def resumen_tematico(texto: str) -> str:
    chunks = [texto[i:i+1024] for i in range(0, len(texto), 1024)]
    resumenes = summarizer(chunks, max_length=300, min_length=100, do_sample=False)
    return "\n\n".join([r['summary_text'] for r in resumenes])

@router.post("/diagnostico/")
async def analizar_audio(ruta: str):
    if not os.path.exists(ruta):
        raise HTTPException(status_code=400, detail="Ruta de audio no válida o archivo no encontrado.")
    resultado = diagnostico_completo(ruta, azure_key=AZURE_SPEECH_KEY, azure_region=AZURE_REGION)
    return {"diagnostico": resultado}

# @router.post("/transcribir")
# def transcribir_audio(req: TranscripcionRequest):
#     link = req.link
#     modo = req.modo_salida

#     if not AZURE_SPEECH_KEY or not AZURE_REGION:
#         raise HTTPException(status_code=500, detail="Faltan credenciales de Azure Speech.")

#     if not validar_url_youtube(str(link)):
#         raise HTTPException(status_code=400, detail="URL inválida de YouTube.")

#     try:
#         download_audio(str(link), AUDIO_FILENAME)
#         convert_mp3_to_wav(AUDIO_FILENAME, WAV_FILENAME)
#         texto_crudo = transcribe_audio_detailed(WAV_FILENAME, AZURE_SPEECH_KEY, AZURE_REGION, LANGUAGE)

#         if not texto_crudo.strip():
#             raise HTTPException(status_code=500, detail="No se obtuvo texto de la transcripción.")

#         if modo == "dialogo":
#             resultado = limpiar_y_formatear_dialogo(texto_crudo)
#         elif modo == "resumen":
#             resultado = resumen_tematico(texto_crudo)
#         else:
#             raise HTTPException(status_code=400, detail="Modo inválido. Usa 'dialogo' o 'resumen'.")

#         return {"resultado": resultado.strip()}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error al procesar audio: {str(e)}")

#     finally:
#         for f in [AUDIO_FILENAME, WAV_FILENAME]:
#             if os.path.exists(f):
#                 os.remove(f)

@router.post("/transcribir")
def transcribir_audio(req: TranscripcionRequest):
    link = req.link
    modo = req.modo_salida

    print(f"DEBUG: Recibida solicitud de transcripción para el link: {link} con modo: {modo}") # Debug print
    print(f"DEBUG: Credenciales de Azure - Key: {AZURE_SPEECH_KEY}, Region: {AZURE_REGION}") # Debug print
    # Validar credenciales de Azure
    
    if not AZURE_SPEECH_KEY or not AZURE_REGION:
        raise HTTPException(status_code=500, detail="Faltan credenciales de Azure Speech.")

    # Convertir link a str aquí una vez para evitar repetirlo y para validar
    link_str = str(link)

    if not validar_url_youtube(link_str):
        raise HTTPException(status_code=400, detail="URL inválida de YouTube.")

    try:
        print(f"DEBUG: Iniciando descarga de audio de: {link_str}") # Debug print
        download_audio(link_str, AUDIO_FILENAME)
        print(f"DEBUG: Audio descargado a: {AUDIO_FILENAME}") # Debug print

        print(f"DEBUG: Iniciando conversión a WAV: {AUDIO_FILENAME} -> {WAV_FILENAME}") # Debug print
        convert_mp3_to_wav(AUDIO_FILENAME, WAV_FILENAME)
        print(f"DEBUG: Archivo WAV creado: {WAV_FILENAME}") # Debug print

        print(f"DEBUG: Iniciando transcripción con Azure Speech...") # Debug print
        texto_crudo = transcribe_audio_detailed(WAV_FILENAME, AZURE_SPEECH_KEY, AZURE_REGION, LANGUAGE)
        print(f"DEBUG: Transcripción de Azure completada. Texto crudo: {texto_crudo[:100]}...") # Debug print

        if not texto_crudo.strip():
            raise HTTPException(status_code=500, detail="No se obtuvo texto de la transcripción.")

        if modo == "dialogo":
            resultado = limpiar_y_formatear_dialogo(texto_crudo)
            print("DEBUG: Formato de diálogo aplicado.") # Debug print
        elif modo == "resumen":
            resultado = resumen_tematico(texto_crudo)
            print("DEBUG: Resumen temático aplicado.") # Debug print
        else:
            raise HTTPException(status_code=400, detail="Modo inválido. Usa 'dialogo' o 'resumen'.")

        print("DEBUG: Proceso completado exitosamente.") # Debug print
        return {"resultado": resultado.strip()}

    except Exception as e:
        # ¡IMPORTANTE! Imprimir el traceback completo aquí
        print(f"ERROR_EN_TRANSCRIPCION: {e}")
        print(traceback.format_exc()) # Esto imprimirá la pila completa de la excepción
        raise HTTPException(status_code=500, detail=f"Error al procesar audio: {str(e)}. Consulta los logs del servidor para más detalles.")

    finally:
        # Asegúrate de que las variables AUDIO_FILENAME y WAV_FILENAME estén definidas antes de este bloque
        # si no lo están globalmente o dentro del try/except
        print(f"DEBUG: Limpiando archivos temporales...") # Debug print
        for f in [AUDIO_FILENAME, WAV_FILENAME]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"DEBUG: Archivo '{f}' eliminado.")
                except Exception as file_e:
                    print(f"ADVERTENCIA: No se pudo eliminar el archivo '{f}': {file_e}")