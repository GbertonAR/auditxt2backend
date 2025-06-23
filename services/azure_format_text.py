### azure_format_text.py
import re

# Si usas Hugging Face para resumen

from services.azure_client import openai_client


    
def limpiar_y_formatear_dialogo(texto: str) -> str:
    """
    Formatea el texto dividiéndolo en frases para mejorar la legibilidad,
    asumiendo que la diarización no está disponible automáticamente.
    """
    dialogo_formateado = []
    # Divide el texto en frases basándose en puntuación final, y luego limpia espacios.
    # Usa un regex para manejar múltiples espacios y la puntuación de forma robusta.
    # Asegúrate de no crear frases vacías.
    frases = re.split(r'(?<=[.?!])\s*', texto)
    for frase in frases:
        frase_limpia = frase.strip()
        if frase_limpia:
            # Podrías añadir un prefijo genérico si quieres simular oradores
            # Por ejemplo:
            # dialogo_formateado.append(f"• {frase_limpia}")
            # O simplemente añadir la frase con un salto de línea
            dialogo_formateado.append(frase_limpia)

    # Unir las frases con dos saltos de línea para un formato más tipo párrafo
    return "\n\n".join(dialogo_formateado)

# def resumen_tematico(texto: str) -> str:
#     """Genera un resumen temático del texto utilizando un modelo Hugging Face."""
#     if not summarizer:
#         return "ERROR: El servicio de resumen no está disponible."
    
#     # El modelo BART tiene un límite de token (1024), por lo que dividimos el texto.
#     # Es una división simple por caracteres, no por tokens, lo cual puede ser impreciso.
#     # Para un manejo de tokens más preciso, usar un tokenizer de transformers.
#     chunk_size = 1000 # Un poco menos de 1024 para dar margen
#     chunks = [texto[i:i + chunk_size] for i in range(0, len(texto), chunk_size)]
    
#     # Procesar cada chunk
#     resumenes = []
#     for i, chunk in enumerate(chunks):
#         try:
#             # Puedes ajustar max_length y min_length según tus necesidades
#             summary = summarizer(chunk, max_length=150, min_length=50, do_sample=False)
#             resumenes.append(summary[0]['summary_text'])
#             print(f"DEBUG: Resumen de chunk {i+1}/{len(chunks)} completado.")
#         except Exception as e:
#             print(f"ADVERTENCIA: No se pudo resumir el chunk {i+1}: {e}")
#             resumenes.append(f"ERROR al resumir parte {i+1}.")
            
#     return "\n\n".join(resumenes)

def resumen_tematico(texto: str) -> str:
    prompt = f"Resumí el siguiente texto en pocas frases:\n\n{texto}"
    response = openai_client.chat.completions.create(
        model="gpt-4",  # o el deployment que tengas configurado
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()
