import pyttsx3
import datetime
import requests
import vosk
import sounddevice as sd
import json

class JARVYS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.DIARY_FILE = "jarvys_diary.txt"
        self.API_KEY = "AIzaSyCGSnQmDyQeNQzF5zCXGNOsBRROv3OtPi0"
        self.GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

        # Load Vosk model
        try:
            self.model = vosk.Model("model/vosk-model-small-es-0.42")
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            print("Please make sure the model is downloaded and in the correct path.")
            exit(1)

    def speak(self, text):
        """Converts text to speech."""
        print(f"JARVYS: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def save_diary_entry(self, entry):
        """Saves a diary entry with a timestamp."""
        with open(self.DIARY_FILE, "a") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp}: {entry}\n")
        print(f"Diary entry saved: {entry}")

    def get_gemini_response(self, user_entry):
        """Gets a response from the Gemini API based on the user's entry."""
        prompt = f"""
Eres JARVYS, un asistente de inteligencia artificial sofisticado y útil para Tony Stark. Tu función principal es actuar como un **diario personal avanzado**.

Cuando recibas una entrada de un usuario:

1.  **Analiza la entrada del diario:** Comprende el contenido, el tema principal, las emociones implícitas (si las hay) y cualquier detalle relevante.
2.  **Genera una respuesta concisa y empática:**
    * Reconoce la entrada del usuario.
    * Ofrece un comentario breve y relevante sobre lo que el usuario ha compartido.
    * Puedes hacer una pregunta reflexiva o proponer una idea para que el usuario pueda expandir su pensamiento en futuras entradas, fomentando la continuidad del diario.
    * Mantén un tono de apoyo, profesional y ligeramente formal, como JARVYS.
    * La respuesta debe ser directa, no divagar.

---

**Ahora, procesa la siguiente entrada del diario del usuario:**

{user_entry}
"""

        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.API_KEY
        }

        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(self.GEMINI_URL, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except requests.exceptions.RequestException as e:
            print(f"Error contacting Gemini API: {e}")
            return "Lo siento, no he podido procesar tu entrada en este momento."

    def listen_for_entry(self):
        """Listens for a diary entry from the user and transcribes it."""
        self.speak("Estoy escuchando. Habla ahora.")
        print("Listening...")

        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16', channels=1) as stream:
            while True:
                data = stream.read(4000)[0]
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    if result['text']:
                        print(f"Recognized: {result['text']}")
                        return result['text']

    def start_diary_session(self):
        """Starts a voice-based diary session."""
        self.speak("Hola, soy JARVYS. ¿Qué te gustaría registrar en tu diario hoy?")

        while True:
            try:
                user_entry = self.listen_for_entry()

                if user_entry and ("salir" in user_entry.lower() or "exit" in user_entry.lower()):
                    self.speak("Entendido. Finalizando sesión de diario.")
                    break

                if user_entry:
                    self.save_diary_entry(user_entry)
                    response = self.get_gemini_response(user_entry)
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