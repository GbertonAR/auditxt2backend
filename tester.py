import os
from dotenv import load_dotenv
from openai import AzureOpenAI

def main():
    load_dotenv()

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION") or "2025-03-01-preview"
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    print("mirar deployments en Azure OpenAI Studio", deployment)

    if not all([azure_endpoint, api_key, deployment]):
        print("❌ Faltan variables de entorno necesarias. Revisa tu .env")
        return

    client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=api_key,
        api_version=api_version
    )

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": "Hola, ¿funciona la conexión con Azure OpenAI?"}]
        )
        print("✅ Respuesta recibida:")
        print(response.choices[0].message.content)
    except Exception as e:
        print("❌ Error al llamar a Azure OpenAI:")
        print(e)

if __name__ == "__main__":
    main()
