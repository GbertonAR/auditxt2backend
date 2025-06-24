# services/azure_client.py
from openai import AzureOpenAI
from Backend_app.config import settings

openai_client = AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version
)
