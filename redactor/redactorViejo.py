from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.ai.openai import OpenAIClient
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = OpenAIClient(
    endpoint=AZURE_OPENAI_ENDPOINT,
    credential=AzureKeyCredential(AZURE_OPENAI_KEY)
)

# Inicialización de FastAPI
app = FastAPI()

# CORS (permite conexión con frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar si es necesario
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de entrada
class PromptRequest(BaseModel):
    prompt: str
    tono: str
    audiencia: str

# Ruta para generar contenido
@app.post("/api/generar")
async def generar_texto(data: PromptRequest):
    system_prompt = (
        f"Eres un redactor oficial del departamento de prensa de un organismo estatal. "
        f"Redacta el contenido solicitado con tono {data.tono}, dirigido al {data.audiencia}. "
        f"Asegúrate de que el mensaje sea claro, institucional, empático y socialmente responsable."
    )

    try:
        response = client.get_chat_completions(
            deployment_name=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": data.prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )

        content = response.choices[0].message.content
        return {"texto": content}

    except Exception as e:
        print("Error al generar texto:", e)
        raise HTTPException(status_code=500, detail="Error al generar contenido")
