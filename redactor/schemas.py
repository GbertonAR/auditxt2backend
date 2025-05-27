# backend/redactor/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, Literal

# class RequestModel(BaseModel):
#     tipo: str
#     tono: str
#     audiencia: str
#     prompt: str

class RequestModel(BaseModel):
    texto: str = Field(..., description="Texto base o instrucciones para generar el contenido")
    tipo: Literal["nota_prensa", "mensaje_oficial", "comunicado", "articulo", "otro"] = Field(
        ..., description="Tipo de contenido a generar"
    )
    tono: Optional[Literal["formal", "informal", "neutral"]] = Field(
        "formal", description="Tono deseado del contenido"
    )
    publico_objetivo: Optional[str] = Field(
        None, description="Público al que va dirigido el texto"
    )
