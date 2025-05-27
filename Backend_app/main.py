# from fastapi import FastAPI
# from .routers import redactor, transcriptor

# app = FastAPI(title="API de Prensa y Transcripción")

# app.include_router(redactor.router, prefix="/api/redactor", tags=["Redactor"])
# app.include_router(transcriptor.router, prefix="/api/transcriptor", tags=["Transcriptor"])
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Auditxt backend funcionando correctamente"}
