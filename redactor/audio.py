# backend/redactor/audio.py (o dentro de redactor.py si prefieres)

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gtts import gTTS
import uuid
import os

router = APIRouter()

class TextoRequest(BaseModel):
    texto: str

@router.post("/texto-audio")
def texto_a_audio(data: TextoRequest):
    try:
        filename = f"{uuid.uuid4()}.mp3"
        filepath = f"audios/{filename}"

        tts = gTTS(text=data.texto, lang="es")
        os.makedirs("audios", exist_ok=True)
        tts.save(filepath)

        return FileResponse(filepath, media_type="audio/mpeg", filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
