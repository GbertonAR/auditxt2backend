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
#from transformers import pipeline
from utils.diagnostico_audio import diagnostico_completo
from Backend_app.config import settings
from pathlib import Path
# Carga las variables de entorno del archivo .env
load_dotenv()

router = APIRouter()

# AUDIO_FILENAME = "output_audio.mp3"
# WAV_FILENAME = "output_audio.wav"
# AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
# AZURE_REGION = os.getenv("AZURE_REGION", "")
# LANGUAGE = "es-ES"
# --- Configuración de Rutas (tomada de settings) ---
# Estas rutas deben estar definidas en tu .env y cargadas por pydantic-settings
# Ejemplo en .env:
# WORK_DIR=C:\GBerton2025\Desarrollos\auditxt2\backend\work
# DATA_WORK=C:\GBerton2025\Desarrollos\auditxt2\backend\work\data

WORK_DIR = settings.work_dir
DATA_WORK = settings.data_work

# Asegurarse de que los directorios existan
os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(DATA_WORK, exist_ok=True)

# Rutas a los ejecutables (asumiendo que están en WORK_DIR)
YT_DLP_EXE = WORK_DIR / "yt-dlp.exe"
FFMPEG_EXE = WORK_DIR / "ffmpeg.exe"
FFPROBE_EXE = WORK_DIR / "ffprobe.exe" # Aunque no se usa directamente en subprocess, es buena práctica tenerlo

# Rutas a los archivos de datos temporales (en DATA_WORK)
AUDIO_FILENAME = DATA_WORK / "audio_descargado.mp3"
WAV_FILENAME = DATA_WORK / "audio_convertido.wav"

# --- Constantes de Azure y Lenguaje (tomadas de settings) ---
# Estas también deben estar en tu .env y cargadas por settings
AZURE_SPEECH_KEY = settings.azure_speech_key
AZURE_REGION = settings.azure_region
# Asume que tienes una variable de lenguaje en settings, o defínela aquí
LANGUAGE = "es-ES" # O settings.azure_speech_language si la agregaste

# --- Router para FastAPI ---
router = APIRouter()

# --- Modelos Pydantic ---
class TranscripcionRequest(BaseModel):
    link: HttpUrl
    modo_salida: str = Query("dialogo", pattern="^(dialogo|resumen)$")

# --- Funciones de Transcripción y Procesamiento ---

def validar_url_youtube(url: str) -> bool:
    """Valida si la URL es de YouTube (simplificado para el ejemplo)."""
    # Usar regex o una librería de terceros para una validación robusta de URL de YouTube
    # Por ahora, se basa en los ejemplos proporcionados.
    return "youtube.com" in url or "youtu.be" in url

def download_audio(url: str, output_file: Path):
    """Descarga audio de YouTube usando yt-dlp y ffmpeg."""
    print("📥 Descargando audio de YouTube...")
    try:
        # Verificar que los ejecutables existen
        # if not YT_DLP_EXE.exists():
        #     raise FileNotFoundError(f"El ejecutable yt-dlp no se encontró en: {YT_DLP_EXE}")
        # if not FFMPEG_EXE.exists():
        #     raise FileNotFoundError(f"El ejecutable ffmpeg no se encontró en: {FFMPEG_EXE}")

        result = subprocess.run(
            [
                str(yt-dlp),
                "-x",
                "--audio-format", "mp3",
                "-o", str(output_file), # Convertir Path a str para subprocess
                url,
                "--ffmpeg-location", str(FFMPEG_EXE) # Convertir Path a str
            ],
            capture_output=True,
            text=True, # Para decodificar stdout/stderr como texto
            check=True # Lanza CalledProcessError si el comando retorna un código de error
        )
        print("✅ Audio descargado correctamente.")
    except FileNotFoundError as e:
        # Relanzar con el mismo mensaje claro
        raise e
    except subprocess.CalledProcessError as e:
        # Imprimir salida del subproceso para depuración
        print(f"ERROR: Fallo al ejecutar yt-dlp. Código de retorno: {e.returncode}")
        print(f"ERROR: stdout: {e.stdout}")
        print(f"ERROR: stderr: {e.stderr}")
        raise Exception(f"❌ Error al descargar audio con yt-dlp: {e.stderr.strip()}")
    except Exception as e:
        print(f"ERROR inesperado en download_audio: {e}")
        raise Exception(f"❌ Error al descargar audio con yt-dlp: {str(e)}")

def convert_mp3_to_wav(mp3_file: Path, wav_file: Path):
    """Convierte un archivo MP3 a WAV usando ffmpeg."""
    print("🎵 Convirtiendo MP3 a WAV...")
    try:
        if not FFMPEG_EXE.exists():
            raise FileNotFoundError(f"El ejecutable ffmpeg no se encontró en: {FFMPEG_EXE}")

        command = [
            str(FFMPEG_EXE), # Convertir Path a str
            "-y",            # Sobrescribir archivo de salida si existe
            "-i", str(mp3_file), # Convertir Path a str
            "-ac", "1",      # Canal de audio (mono)
            "-ar", "16000",  # Tasa de muestreo (16 kHz es común para voz)
            "-sample_fmt", "s16", # Formato de muestra de 16 bits
            str(wav_file)    # Convertir Path a str
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("✅ Conversión completada.")
    except FileNotFoundError as e:
        raise e
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Fallo al ejecutar ffmpeg para conversión. Código de retorno: {e.returncode}")
        print(f"ERROR: stdout: {e.stdout}")
        print(f"ERROR: stderr: {e.stderr}")
        raise Exception(f"❌ Error al convertir MP3 a WAV: {e.stderr.strip()}")
    except Exception as e:
        print(f"ERROR inesperado en convert_mp3_to_wav: {e}")
        raise Exception(f"❌ Error al convertir MP3 a WAV: {str(e)}")

def transcribe_audio_detailed(ruta_wav: Path, azure_key: str, azure_region: str, language: str = "es-ES") -> str:
    """Transcribe audio usando Azure Speech SDK."""
    print("DEBUG: Iniciando transcripción con Azure Speech SDK...")
    speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
    speech_config.speech_recognition_language = language
    audio_input = speechsdk.AudioConfig(filename=str(ruta_wav)) # Convertir Path a str

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    texto = []

    def handle_recognized_event(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            texto.append(evt.result.text)
            # print(f"DEBUG: Texto reconocido parcial: {evt.result.text}") # Debug para ver progreso
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print(f"DEBUG: No se pudo reconocer el habla: {evt.result.no_match_details}")
        elif evt.result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = evt.result.cancellation_details
            print(f"DEBUG: Reconocimiento cancelado: Razón={cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"DEBUG: Código de error={cancellation_details.error_code}")
                print(f"DEBUG: Detalles de error={cancellation_details.error_details}")
                raise Exception(f"Error de Azure Speech: {cancellation_details.error_details}")

    recognizer.recognized.connect(handle_recognized_event)

    done = False
    def stop_cb(evt):
        nonlocal done
        done = True
        print(f"DEBUG: Evento de parada recibido: {evt}")

    recognizer.session_stopped.connect(stop_cb)
    recognizer.canceled.connect(stop_cb)
    recognizer.speech_end_detected.connect(stop_cb) # Añadir para detectar el fin del habla

    print("DEBUG: Iniciando reconocimiento continuo...")
    recognizer.start_continuous_recognition()
    # Espera activa para que el hilo de reconocimiento se ejecute
    timeout_seconds = 300 # Tiempo máximo de espera (ej. 5 minutos)
    start_time = time.time()
    while not done and (time.time() - start_time < timeout_seconds):
        time.sleep(0.5)

    if not done:
        print("ADVERTENCIA: El reconocimiento continuo no finalizó a tiempo. Deteniendo forzosamente.")
    
    recognizer.stop_continuous_recognition()
    print("DEBUG: Reconocimiento continuo detenido.")

    final_text = " ".join(texto).strip()
    if not final_text:
        print("ADVERTENCIA: Transcripción vacía.")
    return final_text

def limpiar_y_formatear_dialogo(texto: str) -> str:
    """
    Formatea el texto dividiéndolo en frases para mejorar la legibilidad,
    asumiendo que la diarización no está disponible automáticamente.
    """
    dialogo_formateado = []
    # Divide el texto en frases basándose en puntuación final, y luego limpia espacios.
    # Usa un regex para manejar múltiples espacios y la puntuación de forma robusta.
    # Asegúrate de no crear frases vacías.
    frases = re.split(r'(?<=[.?!])\s*', texto)
    for frase in frases:
        frase_limpia = frase.strip()
        if frase_limpia:
            # Podrías añadir un prefijo genérico si quieres simular oradores
            # Por ejemplo:
            # dialogo_formateado.append(f"• {frase_limpia}")
            # O simplemente añadir la frase con un salto de línea
            dialogo_formateado.append(frase_limpia)

    # Unir las frases con dos saltos de línea para un formato más tipo párrafo
    return "\n\n".join(dialogo_formateado)

# def limpiar_y_formatear_dialogo(texto: str) -> str:
#     """
#     Formatea el texto en un formato de diálogo simple.
#     Esta función es muy básica y puede necesitar mejoras
#     dependiendo de la calidad de la transcripción cruda y
#     si Azure Speech ya incluye diarización de oradores.
#     """
#     dialogo = []
#     # Intenta dividir por líneas si hay, sino trata el texto completo
#     lineas = texto.splitlines() if "\n" in texto else [texto]

#     for linea in lineas:
#         # Simplificación: si la línea parece tener un orador (ej. "Orador 1:"), úsala
#         # De lo contrario, asume un orador por defecto o simplemente el contenido.
#         if ":" in linea and linea.split(":", 1)[0].strip().endswith("or"): # Heurística simple para "Orador X"
#             orador, contenido = linea.split(":", 1)
#             dialogo.append(f"{orador.strip()}: {contenido.strip()}")
#         else:
#             # Si no hay un orador claro, o se necesita una diarización más avanzada
#             # Esto es un placeholder. La diarización real necesita más lógica o un servicio específico.
#             dialogo.append(linea.strip()) # Por ahora, solo añade la línea

#     return "\n".join(dialogo)
######## TODO ESTO SE BAJA POR FALTA DE ESPACIO EN DISCO
# summarizer = None
# try:
#     # Intentar cargar el pipeline. Podrías incluso verificar si los archivos existen localmente primero.
#     # Esto intenta cargar el modelo de forma optimizada si ya está en caché.
#     summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
#     print("DEBUG: Modelo de resumen cargado correctamente.")
# except (OSError, HfHubPyFilesError, HfHubInvalidUrl) as e:
#     # Error al encontrar/descargar el modelo, o URL inválida en Hugging Face Hub
#     print(f"ERROR CRÍTICO: No se pudieron encontrar/descargar los archivos del modelo de resumen: {e}")
#     print("Asegúrate de que el modelo 'facebook/bart-large-cnn' está disponible y de que tienes conexión a internet si es la primera vez.")
#     # En este caso, podrías considerar que la aplicación no puede iniciarse sin el modelo crítico
#     # raise # Re-lanzar el error para que FastAPI falle al inicio
# except MemoryError:
#     print("ERROR CRÍTICO: Insuficiente memoria RAM para cargar el modelo de resumen.")
#     print("Considera aumentar la RAM de tu sistema o usar un modelo más pequeño.")
#     # raise
# except Exception as e:
#     # Cualquier otro error inesperado
#     print(f"ERROR INESPERADO al cargar el modelo de resumen: {e}")
#     # raise # Podrías decidir que el inicio debe fallar
# finally:
#     if summarizer is None:
#         print("ADVERTENCIA: La funcionalidad de resumen temático no estará disponible debido al fallo en la carga del modelo.")



def resumen_tematico(texto: str) -> str:
    """Genera un resumen temático del texto utilizando un modelo Hugging Face."""
    if not summarizer:
        return "ERROR: El servicio de resumen no está disponible."
    
    # El modelo BART tiene un límite de token (1024), por lo que dividimos el texto.
    # Es una división simple por caracteres, no por tokens, lo cual puede ser impreciso.
    # Para un manejo de tokens más preciso, usar un tokenizer de transformers.
    chunk_size = 1000 # Un poco menos de 1024 para dar margen
    chunks = [texto[i:i + chunk_size] for i in range(0, len(texto), chunk_size)]
    
    # Procesar cada chunk
    resumenes = []
    for i, chunk in enumerate(chunks):
        try:
            # Puedes ajustar max_length y min_length según tus necesidades
            summary = summarizer(chunk, max_length=150, min_length=50, do_sample=False)
            resumenes.append(summary[0]['summary_text'])
            print(f"DEBUG: Resumen de chunk {i+1}/{len(chunks)} completado.")
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo resumir el chunk {i+1}: {e}")
            resumenes.append(f"ERROR al resumir parte {i+1}.")
            
    return "\n\n".join(resumenes)

# --- Endpoints de FastAPI ---

# Este endpoint es más para pruebas directas si tienes un archivo local
@router.post("/diagnostico/")
async def analizar_audio(ruta: str):
    """
    Endpoint para analizar un archivo de audio local.
    Nota: La ruta debe ser accesible desde donde se ejecuta el backend.
    """
    # En un entorno de producción, las rutas de archivo locales raramente son el caso de uso.
    # Aquí se espera una ruta a un archivo de audio ya existente.
    if not Path(ruta).exists():
        raise HTTPException(status_code=400, detail="Ruta de audio no válida o archivo no encontrado.")
    
    # Aquí faltaría la llamada a una función que realice un "diagnóstico completo"
    # Este ejemplo se centra en la transcripción y el resumen.
    # Si 'diagnostico_completo' está en otro módulo, asegúrate de importarlo.
    # Por ahora, simplemente retornaremos un mensaje de que la funcionalidad de diagnóstico
    # no está implementada en este fragmento.
    raise HTTPException(status_code=501, detail="Funcionalidad de diagnóstico completo no implementada en este ejemplo.")


async def send_status_update(client_id: str, status_message: str, progress_value: int = None):
    # En un entorno real, usarías una cola de mensajes (Redis) para esto,
    # ya que la conexión WebSocket podría no estar en el mismo proceso de trabajo.
    if client_id in connections:
        try:
            await connections[client_id].send_json({"status": status_message, "progress": progress_value})
        except Exception as e:
            print(f"No se pudo enviar actualización a {client_id}: {e}")


@router.post("/transcribir")
def transcribir_audio(req: TranscripcionRequest):
    link = req.link
    modo = req.modo_salida

    print(f"DEBUG: Recibida solicitud de transcripción para el link: {link} con modo: {modo}")
    print(f"DEBUG: Credenciales de Azure - Key: {AZURE_SPEECH_KEY[:10]}..., Region: {AZURE_REGION}") # Ocultar clave completa por seguridad en logs

    # Validar credenciales de Azure
    if not AZURE_SPEECH_KEY or not AZURE_REGION:
        raise HTTPException(status_code=500, detail="Faltan credenciales de Azure Speech. Verifica tu archivo .env")

    link_str = str(link)

    if not validar_url_youtube(link_str):
        raise HTTPException(status_code=400, detail="URL inválida de YouTube. Solo se admiten URLs de YouTube.")

    try:
        print(f"DEBUG: Iniciando descarga de audio de: {link_str}")
        download_audio(link_str, AUDIO_FILENAME)
        print(f"DEBUG: Audio descargado a: {AUDIO_FILENAME}")

        print(f"DEBUG: Iniciando conversión a WAV: {AUDIO_FILENAME} -> {WAV_FILENAME}")
        convert_mp3_to_wav(AUDIO_FILENAME, WAV_FILENAME)
        print(f"DEBUG: Archivo WAV creado: {WAV_FILENAME}")

        print(f"DEBUG: Iniciando transcripción con Azure Speech...")
        # Usa el PATH para el archivo WAV directamente
        texto_crudo = transcribe_audio_detailed(WAV_FILENAME, AZURE_SPEECH_KEY, AZURE_REGION, LANGUAGE)
        print(f"DEBUG: Transcripción de Azure completada. Texto crudo (primeros 200 chars): {texto_crudo[:200]}...")

        if not texto_crudo.strip():
            raise HTTPException(status_code=500, detail="No se obtuvo texto de la transcripción. El audio podría estar vacío o ser ininteligible.")

        resultado = ""
        if modo == "dialogo":
            resultado = limpiar_y_formatear_dialogo(texto_crudo)
            print("DEBUG: Formato de diálogo aplicado.")
        elif modo == "resumen":
            resultado = resumen_tematico(texto_crudo)
            print("DEBUG: Resumen temático aplicado.")
        else:
            raise HTTPException(status_code=400, detail="Modo inválido. Usa 'dialogo' o 'resumen'.")

        print("DEBUG: Proceso completado exitosamente.")
        return {"resultado": resultado.strip()}

    except HTTPException:
        # Relanza HTTPException directamente
        raise
    except Exception as e:
        # Imprime el traceback completo para depuración
        print(f"ERROR_EN_TRANSCRIPCION: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error al procesar audio: {str(e)}. Consulta los logs del servidor para más detalles.")

    finally:
        print(f"DEBUG: Limpiando archivos temporales...")
        # Iterar sobre los Path objects y usar .exists() y .unlink()
        for f in [AUDIO_FILENAME, WAV_FILENAME]:
            if f.exists():
                try:
                    f.unlink() # Elimina el archivo
                    print(f"DEBUG: Archivo '{f}' eliminado.")
                except Exception as file_e:
                    print(f"ADVERTENCIA: No se pudo eliminar el archivo '{f}': {file_e}")