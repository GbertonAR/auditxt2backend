# app.py Aplicacion principal del backend de Auditxt
# Este archivo configura FastAPI, CORS y registra los routers necesarios.

import uvicorn
#from fastapi import FastAPI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from redactor.redactor import router as redactor_router
from transcriptor.transcriptor import router as transcriptor_router



app = FastAPI()

#app.include_router(transcriptor_router)

# CORS para permitir requests desde frontend (ej. localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # ajusta esto en producción para mayor seguridad (ej. ["http://localhost:5173"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
# Todas las rutas definidas en 'redactor_router' ahora tendrán el prefijo '/api'
app.include_router(redactor_router, prefix="/api")

app.include_router(transcriptor_router, prefix="/api")  # ✅ usa /api


# Puedes tener una forma de mapear job_id a conexiones WebSocket
# (Esto es una simplificación; en una app real, usarías una cola de mensajes como Redis Pub/Sub)
connections: dict[str, WebSocket] = {}

@app.websocket("/ws/transcription_status")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    connections[client_id] = websocket
    try:
        while True:
            # Puedes recibir mensajes del cliente si quieres, pero para progreso
            # el servidor es el que envía.
            # Este loop evita que la conexión se cierre prematuramente si no hay tráfico del cliente.
            await websocket.receive_text()
    except WebSocketDisconnect:
        del connections[client_id]
        print(f"Cliente {client_id} desconectado.")
    except Exception as e:
        print(f"Error en WebSocket para {client_id}: {e}")

# Ruta raíz para probar que el backend funciona
@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <title>Auditxt Backend</title>
        <style>
            body {
                background-color: #003366;
                color: white;
                font-family: Arial, sans-serif;
                font-weight: bold;
                text-align: center;
                padding-top: 100px;
            }
        </style>
    </head>
    <body>
        <h1>Auditxt backend funcionando correctamente</h1>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ELIMINADO: Ya no necesitamos este endpoint /generar aquí. Testeos varios
# La lógica de generación de contenido se maneja exclusivamente en redactor/redactor.py
# y es accesible a través de /api/generar.
#
# @app.post("/generar")
# async def generar_contenido(request: RequestModel):
#     print(f"Recibido: {request}")
#     return {
#         "message": "Contenido generado exitosamente",
#         "data": request.dict()
#     }

# Ejecutar localmente con python app.py (opcional)
if __name__ == "__main__":
    # Para desarrollo local:
    #uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
    pass  # No ejecutar automáticamente al importar este módulo
    # Para despliegue en producción (ej. Azure App Service):
    # El puerto puede ser configurado por la plataforma (usualmente 80 o 8000).
    # Azure App Service suele usar la variable de entorno WEBSITES_PORT si la configuras.
    # Si no, a menudo el puerto por defecto es 8000.
    #uvicorn.run("app:app", host="0.0.0.0", port=8000)
    # Considera quitar 'reload=True' en producción para mejor rendimiento y estabilidad.