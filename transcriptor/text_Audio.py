import azure.cognitiveservices.speech as speechsdk

speech_config = speechsdk.SpeechConfig(subscription="WjLxIy0kMKmebYud4wE3oJA8RIzd1632JKIsJhg1hgCqrPr78ZsIJQQJ99BEAC4f1cMXJ3w3AAAYACOGl4TH", region="westus")
speech_config.speech_synthesis_language = "de-AT"
speech_config.speech_synthesis_voice_name = voz

audio_config = speechsdk.audio.AudioOutputConfig(filename=nombre_archivo)

synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

result = synthesizer.speak_text_async(texto).get()

if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Audio generado exitosamente: {nombre_archivo}")
else:
        print("Error al generar el audio:", result.reason)

# except Exception as e:
#     print("Excepción:", e)
