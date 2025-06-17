from gtts import gTTS
import os

def texto_a_audio(texto: str, nombre_archivo: str = "salida.mp3", idioma: str = "es"):
    try:
        tts = gTTS(text=texto, lang=idioma)
        tts.save(nombre_archivo)
        tts = gTTS(text=texto, lang="en")
        tts.save("salidaEN.mp3")
        tts = gTTS(text=texto, lang="fr")
        tts.save("salidaFR.mp3")
        print(f"Audio guardado como {nombre_archivo}")
        return nombre_archivo
    except Exception as e:
        print("Error al generar el audio:", e)
        return None

# Ejemplo de uso
if __name__ == "__main__":
    texto = input("Introduce el texto a convertir en audio: ")
    texto_a_audio(texto)
