# services/azure_client.py
import os
from openai import AzureOpenAI

# Asegúrate de que estas variables de entorno estén configuradas
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = "2024-02-01" # o la versión que estés usando

openai_client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=api_key,
    api_version=api_version
)