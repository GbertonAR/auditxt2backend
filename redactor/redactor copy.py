from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AzureOpenAI
from Backend_app.config import settings
import logging

# Configurar logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()

# Configuración de Azure OpenAI
AZURE_OPENAI_KEY = settings.azure_openai_key
AZURE_OPENAI_ENDPOINT = settings.azure_openai_endpoint  
AZURE_DEPLOYMENT_NAME = settings.azure_openai_deployment

logger.info(f"🔑 Cargando configuración Azure OpenAI")
logger.info(f"Endpoint: {AZURE_OPENAI_ENDPOINT}")
logger.info(f"Deployment: {AZURE_DEPLOYMENT_NAME}")

# Cliente Azure OpenAI (compatible con openai>=1.0.0)
client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2024-12-01-preview",
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

# Modelo de entrada
class RedaccionRequest(BaseModel):
    titulo: str
    contenido: str
    tono: str = "institucional"
    audiencia: str = "público general"

# Función para generar contenido con Azure OpenAI
async def generar_contenido_ia(prompt: str, tono: str, audiencia: str) -> str:
    system_prompt = (
        f"Eres un redactor oficial del departamento de prensa de un organismo estatal. "
        f"Redacta el contenido solicitado con tono {tono}, dirigido al {audiencia}. "
        f"Asegúrate de que el mensaje sea claro, institucional, empático y socialmente responsable."
    )

    try:
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ Error al generar contenido IA: {str(e)}")
        raise
# async def generar_contenido_ia(prompt: str, tono: str, audiencia: str) -> str:
#     system_prompt = (
#         f"Eres un redactor oficial del departamento de prensa de un organismo estatal. "
#         f"Redacta el contenido solicitado con tono {tono}, dirigido al {audiencia}. "
#         f"Asegúrate de que el mensaje sea claro, institucional, empático y socialmente responsable."
#     )

#     try:
#         logger.info("📨 Enviando solicitud a Azure OpenAI...")
#         response = await client.chat.completions.create(
#             deployment_id=AZURE_DEPLOYMENT_NAME,
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.7,
#             max_tokens=800
#         )
#         resultado = response.choices[0].message.content
#         logger.info("✅ Contenido generado correctamente")
#         return resultado

#     except Exception as e:
#         logger.error(f"❌ Error al generar contenido con OpenAI: {str(e)}")
#         raise

# Ruta de la API
@router.post("/generar")
async def generar_contenido(data: RedaccionRequest):
    print(f"📥 Solicitud recibida: {data}")
    try:
        logger.info(f"📥 Solicitud recibida: {data}")
        resultado = await generar_contenido_ia(data.contenido, data.tono, data.audiencia)
        return {"titulo": data.titulo, "resultado": resultado}
    except Exception as e:
        logger.error(f"❌ Error en endpoint /generar: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al generar contenido: {str(e)}")
