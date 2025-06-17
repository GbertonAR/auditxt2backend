# # Backend_app/main.py

from fastapi import FastAPI
from Backend_app.routers import transcriptor
from Backend_app.routers import transcriptor_audio

app = FastAPI(title="API Auditxt")

app.include_router(transcriptor.router, prefix="/api/transcriptor", tags=["Transcriptor"])
app.include_router(transcriptor_audio.router, prefix="/api/transcribir-archivo", tags=["transcriptor_audio"])

@app.get("/")
def root():
    return {"message": "Auditxt backend funcionando correctamente"}
