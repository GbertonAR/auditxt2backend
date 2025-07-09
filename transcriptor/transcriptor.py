### Transcriptor de Audio a Texto para Web Auditxt2
# Este módulo maneja la transcripción de audio desde YouTube a texto
from dotenv import load_dotenv
import os
import subprocess
import re
import traceback # Importar traceback
import time
# Asegúrate de que yt-dlp está instalado en tu entorno (pip install yt-dlp)
# Si lo usas como ejecutable, debe estar accesible en el PATH o en la ruta especificada.
import yt_dlp 
import azure.cognitiveservices.speech as speechsdk
from fastapi import APIRouter, HTTPException, Query, Request, File, UploadFile, status
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional, Dict, Any
from pathlib import Path
import shutil

# Importa las configuraciones de tu aplicación (asegúrate de que este archivo exista y esté bien configurado)
from Backend_app.config import settings

# Importa el cliente de OpenAI (asumiendo que está en services/azure_client.py)
# ESTE ARCHIVO DEBE EXISTIR Y CONFIGURAR 'openai_client'
from services.azure_client import openai_client 

router = APIRouter()

# --- Configuración de Rutas (tomada de settings) ---
# Estas rutas deben estar definidas en tu .env y cargadas por pydantic-settings
# Ejemplo en .env:
# WORK_DIR_PATH=/tmp/work # o C:\GBerton2025\Desarrollos\auditxt2\backend\work en Windows
# DATA_WORK_PATH=/tmp/work/data # o C:\GBerton2025\Desarrollos\auditxt2\backend\work\data en Windows

# Las variables en settings ya deben ser objetos Path si están configuradas así en Backend_app/config.py
WORK_DIR = settings.work_dir
DATA_WORK = settings.data_work

# Asegurarse de que los directorios existan
WORK_DIR.mkdir(parents=True, exist_ok=True)
DATA_WORK.mkdir(parents=True, exist_ok=True)

# Rutas a los ejecutables
# IMPORTANTÍSIMO: Estas rutas deben apuntar a los ejecutables DE LINUX en Azure App Service,
# o deben estar en el PATH del contenedor.
# Si estás ejecutando en Windows, pueden ser rutas de Windows.
# Para despliegue en Azure, se recomienda usar binarios de Linux y asegurar su disponibilidad.
YT_DLP_EXE = WORK_DIR / "yt-dlp.exe" # En Linux, no suele llevar .exe
FFMPEG_EXE = WORK_DIR / "ffmpeg.exe" # En Linux
FFPROBE_EXE = WORK_DIR / "ffprobe.exe" # En Linux (aunque no se usa directamente aquí, es buena práctica)

# Rutas a los archivos de datos temporales (en DATA_WORK)
AUDIO_FILENAME = DATA_WORK / "audio_descargado.mp3"
WAV_FILENAME = DATA_WORK / "audio_convertido.wav"

# --- Constantes de Azure y Lenguaje (tomadas de settings) ---
AZURE_SPEECH_KEY = settings.azure_speech_key
AZURE_REGION = settings.azure_speech_region
LANGUAGE = "es-ES" # O "es-ES" si no lo tienes en settings

# --- Modelos Pydantic ---
class TranscripcionRequest(BaseModel):
    link: HttpUrl
    modo_salida: str = Query("dialogo", pattern="^(dialogo|resumen)$")

# --- Funciones de Transcripción y Procesamiento ---

def validar_url_youtube(url: str) -> bool:
    """Valida si la URL es de YouTube (simplificado para el ejemplo)."""
    # Para una validación robusta de URLs de YouTube, considera usar una librería
    # o una expresión regular más compleja.
    # Los ejemplos proporcionados ("http://googleusercontent.com/youtube.com/...")
    # son poco comunes para URLs directas de YouTube. Un ejemplo típico es:
    # "https://www.youtube.com/watch?v=..." o "https://youtu.be/..."
    return "youtube.com" in url or "youtu.be" in url

def _check_executable(exe_path: Path):
    """Verifica si un ejecutable existe y tiene permisos de ejecución."""
    if not exe_path.is_file():
        raise FileNotFoundError(f"El ejecutable '{exe_path.name}' no se encontró en: {exe_path}")
    if not os.access(exe_path, os.X_OK):
        raise PermissionError(f"El ejecutable '{exe_path.name}' no tiene permisos de ejecución: {exe_path}")


def download_audio(url: str, output_file: Path):
    """Descarga audio de YouTube usando yt-dlp y ffmpeg."""
    print("📥 Descargando audio de YouTube...")
    try:
        _check_executable(YT_DLP_EXE)
        _check_executable(FFMPEG_EXE) # ffmpeg es necesario para yt-dlp para extraer audio a mp3

        command = [
            str(YT_DLP_EXE),
            "-x", # Extraer audio
            "--audio-format", "mp3", # Formato de audio
            "-o", str(output_file), # Ruta de salida
            url, # URL de YouTube
            "--ffmpeg-location", str(FFMPEG_EXE) # Ruta al ejecutable de ffmpeg
        ]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True, # Para decodificar stdout/stderr como texto
            check=True # Lanza CalledProcessError si el comando retorna un código de error
        )
        print("✅ Audio descargado correctamente.")
    except FileNotFoundError as e:
        print(f"ERROR: Ejecutable no encontrado: {e}")
        raise HTTPException(status_code=500, detail=f"Error del servidor: {e}. Asegúrate de que yt-dlp y ffmpeg estén instalados y accesibles.")
    except PermissionError as e:
        print(f"ERROR: Permisos incorrectos en ejecutable: {e}")
        raise HTTPException(status_code=500, detail=f"Error del servidor: {e}. Asegúrate de que yt-dlp y ffmpeg tienen permisos de ejecución.")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Fallo al ejecutar yt-dlp. Código de retorno: {e.returncode}")
        print(f"ERROR: stdout: {e.stdout}")
        print(f"ERROR: stderr: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"❌ Error al descargar audio con yt-dlp: {e.stderr.strip()}")
    except Exception as e:
        print(f"ERROR inesperado en download_audio: {e}")
        raise HTTPException(status_code=500, detail=f"❌ Error al descargar audio: {str(e)}")

def convert_mp3_to_wav(mp3_file: Path, wav_file: Path):
    """Convierte un archivo MP3 a WAV usando ffmpeg."""
    print("🎵 Convirtiendo MP3 a WAV...")
    try:
        _check_executable(FFMPEG_EXE)

        command = [
            str(FFMPEG_EXE),
            "-y",               # Sobrescribir archivo de salida si existe
            "-i", str(mp3_file), # Archivo de entrada MP3
            "-ac", "1",         # Canal de audio (mono)
            "-ar", "16000",     # Tasa de muestreo (16 kHz es común para voz)
            "-sample_fmt", "s16", # Formato de muestra de 16 bits
            str(wav_file)       # Archivo de salida WAV
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("✅ Conversión completada.")
    except FileNotFoundError as e:
        print(f"ERROR: Ejecutable ffmpeg no encontrado: {e}")
        raise HTTPException(status_code=500, detail=f"Error del servidor: {e}. Asegúrate de que ffmpeg esté instalado y accesible.")
    except PermissionError as e:
        print(f"ERROR: Permisos incorrectos en ffmpeg: {e}")
        raise HTTPException(status_code=500, detail=f"Error del servidor: {e}. Asegúrate de que ffmpeg tiene permisos de ejecución.")
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Fallo al ejecutar ffmpeg para conversión. Código de retorno: {e.returncode}")
        print(f"ERROR: stdout: {e.stdout}")
        print(f"ERROR: stderr: {e.stderr}")
        raise HTTPException(status_code=500, detail=f"❌ Error al convertir MP3 a WAV: {e.stderr.strip()}")
    except Exception as e:
        print(f"ERROR inesperado en convert_mp3_to_wav: {e}")
        raise HTTPException(status_code=500, detail=f"❌ Error al convertir MP3 a WAV: {str(e)}")

def transcribe_audio_detailed(ruta_wav: Path, azure_key: str, AZURE_REGION: str, language: str = "es-ES") -> str:
    """Transcribe audio usando Azure Speech SDK."""
    print("DEBUG: Iniciando transcripción con Azure Speech SDK...")
    
    # Validar que las credenciales no estén vacías antes de intentar conectarse
    if not azure_key:
        raise ValueError("La clave de Azure Speech no puede estar vacía.")
    if not AZURE_REGION:
        raise ValueError("La región de Azure Speech no puede estar vacía.")

    speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=AZURE_REGION)
    speech_config.speech_recognition_language = language
    audio_input = speechsdk.AudioConfig(filename=str(ruta_wav)) # Convertir Path a str

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)

    texto = []

    def handle_recognized_event(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            texto.append(evt.result.text)
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            print(f"DEBUG: No se pudo reconocer el habla: {evt.result.no_match_details}")
        elif evt.result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = evt.result.cancellation_details
            print(f"DEBUG: Reconocimiento cancelado: Razón={cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"DEBUG: Código de error={cancellation_details.error_code}")
                print(f"DEBUG: Detalles de error={cancellation_details.error_details}")
                # Lanzar una excepción más específica para este caso
                raise Exception(f"Error de Azure Speech: {cancellation_details.error_details} (Código: {cancellation_details.error_code})")

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
    timeout_seconds = 300 # Tiempo máximo de espera (ej. 5 minutos para audios largos)
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
            dialogo_formateado.append(frase_limpia)

    # Unir las frases con dos saltos de línea para un formato más tipo párrafo
    return "\n\n".join(dialogo_formateado)

def resumen_tematico(texto: str) -> str:
    """Genera un resumen temático del texto utilizando Azure OpenAI."""
    if openai_client is None:
        print("ERROR: openai_client no está inicializado. No se puede generar resumen.")
        raise HTTPException(status_code=500, detail="El servicio de resumen no está disponible. Contacta al administrador.")

    prompt = f"Resumí el siguiente texto en pocas frases:\n\n{texto}"
    try:
        response = openai_client.chat.completions.create(
            model=settings.azure_openai_deployment_name,  # Usa el nombre de despliegue de tu modelo
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR: Fallo al generar resumen con Azure OpenAI: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error al generar resumen: {str(e)}")

# --- Endpoints de FastAPI ---

@router.post("/diagnostico/")
async def analizar_audio(ruta: str):
    """
    Endpoint para analizar un archivo de audio local.
    Nota: La ruta debe ser accesible desde donde se ejecuta el backend.
    """
    ruta_path = Path(ruta)
    if not ruta_path.is_file():
        raise HTTPException(status_code=400, detail="Ruta de audio no válida o archivo no encontrado.")
    
    # Aquí se esperaría la llamada a una función que realice un "diagnóstico completo"
    # Este ejemplo se centra en la transcripción y el resumen.
    # Si 'diagnostico_completo' está en otro módulo, asegúrate de importarlo y que funcione con Path.
    try:
        # Asumiendo que diagnostico_completo espera una ruta de tipo Path
        reporte = diagnostico_completo(ruta_path)
        return {"diagnostico": reporte}
    except Exception as e:
        print(f"ERROR en /diagnostico: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error al ejecutar el diagnóstico: {str(e)}")


@router.post("/transcribir")
async def transcribir_audio_endpoint(req: TranscripcionRequest): # Cambiado el nombre para evitar conflicto
    link = req.link
    modo = req.modo_salida

    print(f"DEBUG: Recibida solicitud de transcripción para el link: {link} con modo: {modo}")
    print(f"DEBUG: Credenciales de Azure Speech - Key: {AZURE_SPEECH_KEY[:10]}..., Region: {AZURE_REGION}") # Ocultar clave completa por seguridad en logs

    # Validar credenciales de Azure Speech
    if not AZURE_SPEECH_KEY or not AZURE_REGION:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Faltan credenciales de Azure Speech. Verifica tu configuración.")

    link_str = str(link)

    if not validar_url_youtube(link_str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="URL inválida de YouTube. Solo se admiten URLs de YouTube.")

    try:
        print(f"DEBUG: Iniciando descarga de audio de: {link_str}")
        download_audio(link_str, AUDIO_FILENAME)
        print(f"DEBUG: Audio descargado a: {AUDIO_FILENAME}")

        print(f"DEBUG: Iniciando conversión a WAV: {AUDIO_FILENAME} -> {WAV_FILENAME}")
        convert_mp3_to_wav(AUDIO_FILENAME, WAV_FILENAME)
        print(f"DEBUG: Archivo WAV creado: {WAV_FILENAME}")

        print(f"DEBUG: Iniciando transcripción con Azure Speech...")
        texto_crudo = transcribe_audio_detailed(WAV_FILENAME, AZURE_SPEECH_KEY, AZURE_REGION, LANGUAGE)
        print(f"DEBUG: Transcripción de Azure completada. Texto crudo (primeros 200 chars): {texto_crudo[:200]}...")

        if not texto_crudo.strip():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="No se obtuvo texto de la transcripción. El audio podría estar vacío o ser ininteligible.")

        resultado = ""
        if modo == "dialogo":
            resultado = limpiar_y_formatear_dialogo(texto_crudo)
            print("DEBUG: Formato de diálogo aplicado.")
        elif modo == "resumen":
            resultado = resumen_tematico(texto_crudo) # Llama a la función de resumen
            print("DEBUG: Resumen temático aplicado.")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Modo inválido. Usa 'dialogo' o 'resumen'.")

        print("DEBUG: Proceso completado exitosamente.")
        return {"transcripcion": resultado.strip()}

    except HTTPException:
        # Relanza HTTPException directamente si ya fue capturada y generada
        raise
    except Exception as e:
        # Captura cualquier otra excepción inesperada
        print(f"ERROR_EN_TRANSCRIPCION: {e}")
        print(traceback.format_exc()) # Imprime el traceback completo para depuración
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error al procesar audio: {str(e)}. Consulta los logs del servidor para más detalles.")

    finally:
        print(f"DEBUG: Limpiando archivos temporales en {DATA_WORK}...")
        # Iterar sobre los Path objects y usar .exists() y .unlink()
        for f in [AUDIO_FILENAME, WAV_FILENAME]:
            if f.exists():
                try:
                    f.unlink() # Elimina el archivo
                    print(f"DEBUG: Archivo '{f.name}' eliminado.")
                except Exception as file_e:
                    print(f"ADVERTENCIA: No se pudo eliminar el archivo '{f.name}': {file_e}")