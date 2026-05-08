import datetime
import json
import os
import sys
from pathlib import Path

import pyttsx3
import requests
import sounddevice as sd
import vosk
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# Ruta del modelo relativa a este archivo (funciona desde cualquier cwd)
_MODEL_DIR = Path(__file__).resolve().parent / "model" / "vosk-model-small-es-0.42"


class JARVYS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.DIARY_FILE = "jarvys_diary.txt"
        self.API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
        self.OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

        try:
            self.model = vosk.Model(str(_MODEL_DIR))
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            print(f"Comprueba que el modelo exista en: {_MODEL_DIR}")
            sys.exit(1)

    def speak(self, text):
        """Converts text to speech."""
        print(f"JARVYS: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def save_diary_entry(self, entry):
        """Saves a diary entry with a timestamp."""
        with open(self.DIARY_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp}: {entry}\n")
        print(f"Diary entry saved: {entry}")

    @staticmethod
    def _extract_openrouter_text(body):
        """Extrae el texto de la respuesta JSON de Open Router; None si no hay texto usable."""
        if not isinstance(body, dict):
            return None
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            print(f"Open Router API error: {err.get('message')}")
            return None
        choices = body.get("choices")
        if not choices or not isinstance(choices, list):
            return None
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        if not isinstance(message, dict):
            return None
        text = message.get("content")
        if text is None:
            return None
        return text.strip()

    def get_openrouter_response(self, user_entry):
        """Gets a response from the Open Router API based on the user's entry."""
        if not self.API_KEY:
            print(
                "OPENROUTER_API_KEY no está definida. "
                "Exporta la clave o define la variable de entorno antes de ejecutar."
            )
            return (
                "No puedo conectar con el modelo: falta la clave de API. "
                "Configura OPENROUTER_API_KEY y vuelve a intentarlo."
            )

        system_prompt = """Eres JARVYS, un asistente de inteligencia artificial sofisticado y útil para Tony Stark. Tu función principal es actuar como un diario personal avanzado.

Cuando recibas una entrada de un usuario:

1. Analiza la entrada del diario: Comprende el contenido, el tema principal, las emociones implícitas (si las hay) y cualquier detalle relevante.
2. Genera una respuesta concisa y empática:
   - Reconoce la entrada del usuario.
   - Ofrece un comentario breve y relevante sobre lo que el usuario ha compartido.
   - Puedes hacer una pregunta reflexiva o proponer una idea para que el usuario pueda expandir su pensamiento en futuras entradas, fomentando la continuidad del diario.
   - Mantén un tono de apoyo, profesional y ligeramente formal, como JARVYS.
   - La respuesta debe ser directa, no divagar."""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.API_KEY}",
        }

        data = {
            "model": "openrouter/auto",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_entry,
                }
            ]
        }

        try:
            response = requests.post(
                self.OPENROUTER_URL, headers=headers, json=data, timeout=60
            )
            response.raise_for_status()
            text = self._extract_openrouter_text(response.json())
            if text:
                return text
            return "Lo siento, no he podido obtener una respuesta válida del modelo."
        except requests.exceptions.RequestException as e:
            print(f"Error contacting Open Router API: {e}")
            return "Lo siento, no he podido procesar tu entrada en este momento."

    def listen_for_entry(self):
        """Listens for a diary entry from the user and transcribes it."""
        self.speak("Estoy escuchando. Habla ahora.")
        print("Listening...")

        with sd.RawInputStream(
            samplerate=16000, blocksize=8000, dtype="int16", channels=1
        ) as stream:
            while True:
                data = stream.read(4000)[0]
                if self.recognizer.AcceptWaveform(bytes(data)):
                    result = json.loads(self.recognizer.Result())
                    if result.get("text"):
                        print(f"Recognized: {result['text']}")
                        return result["text"]

    def start_diary_session(self):
        """Starts a voice-based diary session."""
        self.speak("Hola, soy JARVYS. ¿Qué te gustaría registrar en tu diario hoy?")

        while True:
            try:
                user_entry = self.listen_for_entry()

                if user_entry and (
                    "salir" in user_entry.lower() or "exit" in user_entry.lower()
                ):
                    self.speak("Entendido. Finalizando sesión de diario.")
                    break

                if user_entry:
                    self.save_diary_entry(user_entry)
                    response = self.get_openrouter_response(user_entry)
                    self.speak(response)

            except (KeyboardInterrupt, EOFError):
                self.speak("Finalizando sesión de diario.")
                break
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                self.speak("Lo siento, ha ocurrido un error inesperado.")
                break


if __name__ == "__main__":
    jarvys = JARVYS()
    jarvys.start_diary_session()
