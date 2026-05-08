import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pyttsx3
import requests
import sounddevice as sd
import vosk
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

_MODEL_DIR = Path(__file__).resolve().parent / "model" / "vosk-model-small-es-0.42"

# ANSI colors
_C_JARVIS = "\033[96m"   # cyan brillante — JARVIS
_C_USER   = "\033[93m"   # amarillo       — usuario
_C_DIM    = "\033[90m"   # gris           — sistema/partial
_C_RESET  = "\033[0m"

_SYSTEM_PROMPT = """Eres JARVIS, una inteligencia artificial avanzada. Tu función es actuar como diario personal de voz.

Estilo de respuesta:
- Tono: preciso, seco, profesional. Como el JARVIS de Iron Man: inteligente, eficiente, con ligero sarcasmo ocasional. Nunca condescendiente ni excesivamente empático.
- Extensión: máximo 2-3 oraciones. Sin divagar.
- No uses el nombre del usuario a menos que él lo haya mencionado explícitamente.
- No preguntes "¿cómo te sientes?" ni uses frases terapéuticas.
- Sí puedes hacer una pregunta breve y relevante para profundizar en la entrada, si tiene sentido.
- Responde siempre en el mismo idioma que el usuario."""


class JARVIS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self._set_spanish_voice()
        self.DIARY_FILE = "jarvis_diary.txt"
        self.history = []

        self._select_backend()

        try:
            self.model = vosk.Model(str(_MODEL_DIR))
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            print(f"Comprueba que el modelo exista en: {_MODEL_DIR}")
            sys.exit(1)

    def _set_spanish_voice(self):
        voices = self.engine.getProperty("voices")
        spanish = next((v for v in voices if "es" in v.id and "419" not in v.id), None)
        if spanish:
            self.engine.setProperty("voice", spanish.id)
            print(f"{_C_DIM}Voz: {spanish.name}{_C_RESET}")

    def _select_backend(self):
        print(f"\n{_C_JARVIS}╔══════════════════════════════╗")
        print("║   JARVIS — Selección de LLM  ║")
        print(f"╚══════════════════════════════╝{_C_RESET}")
        print("  1) OpenRouter  (nube)")
        print("  2) Ollama      (local)")

        while True:
            choice = input("\nElige backend [1/2]: ").strip()
            if choice in ("1", "2"):
                break
            print("  → Escribe 1 o 2")

        if choice == "1":
            api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
            if not api_key:
                print("  → OPENROUTER_API_KEY no encontrada en .env")
                sys.exit(1)
            self.llm_url = "https://openrouter.ai/api/v1/chat/completions"
            self.llm_model = "google/gemini-flash-1.5"
            self.llm_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            print(f"  → OpenRouter / {self.llm_model}\n")
        else:
            self._select_ollama_model()

    def _select_ollama_model(self):
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
        except FileNotFoundError:
            print("  → Ollama no encontrado. Instala desde https://ollama.com")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print("  → Ollama no responde.")
            sys.exit(1)

        lines = result.stdout.strip().splitlines()
        models = [line.split()[0] for line in lines[1:] if line.strip()]

        if not models:
            print("  → Sin modelos en Ollama. Descarga uno: ollama pull llama3.2")
            sys.exit(1)

        print("\nModelos disponibles:")
        for i, m in enumerate(models, 1):
            print(f"  {i}) {m}")

        while True:
            raw = input(f"\nElige modelo [1-{len(models)}]: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(models):
                break
            print(f"  → Escribe un número entre 1 y {len(models)}")

        self.llm_url = "http://localhost:11434/v1/chat/completions"
        self.llm_model = models[int(raw) - 1]
        self.llm_headers = {"Content-Type": "application/json"}
        print(f"  → Ollama / {self.llm_model}\n")

    def speak(self, text):
        print(f"\n{_C_JARVIS}JARVIS:{_C_RESET} {text}\n")
        self.engine.say(text)
        self.engine.runAndWait()

    def save_diary_entry(self, entry):
        with open(self.DIARY_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp}: {entry}\n")

    @staticmethod
    def _extract_text(body):
        if not isinstance(body, dict):
            return None
        err = body.get("error")
        if isinstance(err, dict) and err.get("message"):
            print(f"API error: {err.get('message')}")
            return None
        choices = body.get("choices")
        if not choices or not isinstance(choices, list):
            return None
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        if not isinstance(message, dict):
            return None
        text = message.get("content")
        return text.strip() if text else None

    def get_llm_response(self, user_entry):
        self.history.append({"role": "user", "content": user_entry})

        data = {
            "model": self.llm_model,
            "messages": [{"role": "system", "content": _SYSTEM_PROMPT}] + self.history,
        }

        try:
            response = requests.post(
                self.llm_url, headers=self.llm_headers, json=data, timeout=60
            )
            response.raise_for_status()
            text = self._extract_text(response.json())
            if text:
                self.history.append({"role": "assistant", "content": text})
                return text
            self.history.pop()
            return "Sin respuesta válida del modelo."
        except requests.exceptions.RequestException as e:
            print(f"Error contacting LLM: {e}")
            self.history.pop()
            return "No se pudo procesar la entrada."

    def listen_for_entry(self):
        last_partial = ""
        stable_count = 0
        STABLE_FRAMES = 10  # 10 × 0.25s = ~2.5s sin cambio → forzar resultado
        term_width = shutil.get_terminal_size().columns

        with sd.RawInputStream(
            samplerate=16000, blocksize=8000, dtype="int16", channels=1
        ) as stream:
            print(f"{_C_DIM}🎤  escuchando...{_C_RESET}", flush=True)
            while True:
                data, _ = stream.read(4000)
                if self.recognizer.AcceptWaveform(bytes(data)):
                    result = json.loads(self.recognizer.Result())
                    if result.get("text"):
                        # Limpia línea del partial y muestra entrada final
                        print(f"\r\033[K{_C_USER}TÚ:{_C_RESET} {result['text']}")
                        return result["text"]
                else:
                    partial = json.loads(self.recognizer.PartialResult()).get("partial", "")
                    if partial and partial != last_partial:
                        # Truncar al ancho del terminal para evitar wrap
                        prefix = "    … "
                        max_len = term_width - len(prefix) - 1
                        display = partial[:max_len] + ("…" if len(partial) > max_len else "")
                        print(f"\r\033[K{_C_DIM}{prefix}{display}{_C_RESET}", end="", flush=True)
                    if partial and partial == last_partial:
                        stable_count += 1
                        if stable_count >= STABLE_FRAMES:
                            final = json.loads(self.recognizer.FinalResult()).get("text", "").strip()
                            print()
                            if final:
                                print(f"\r\033[K{_C_USER}TÚ:{_C_RESET} {final}")
                                return final
                            stable_count = 0
                            last_partial = ""
                    else:
                        last_partial = partial
                        stable_count = 0

    def start_diary_session(self):
        self.speak("JARVIS en línea. Listo para registrar.")

        while True:
            try:
                user_entry = self.listen_for_entry()

                if user_entry and (
                    "salir" in user_entry.lower() or "exit" in user_entry.lower()
                ):
                    self.speak("Sesión finalizada.")
                    break

                if user_entry:
                    self.save_diary_entry(user_entry)
                    response = self.get_llm_response(user_entry)
                    self.speak(response)

            except (KeyboardInterrupt, EOFError):
                self.speak("Sesión finalizada.")
                break
            except Exception as e:
                print(f"Error inesperado: {e}")
                self.speak("Error inesperado. Reintentando.")


if __name__ == "__main__":
    jarvis = JARVIS()
    jarvis.start_diary_session()
