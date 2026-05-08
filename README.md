# J.A.R.V.I.S. (JARVYS)

Asistente de diario por voz en español: reconoce lo que dices con **Vosk**, guarda entradas en un archivo de texto y responde con **OpenRouter** (modelo `google/gemini-flash-1.5`).

## Requisitos

- Python 3.10+ recomendado.
- Micrófono y permisos de audio.
- Clave de API de [OpenRouter](https://openrouter.ai/keys).

### Sistema (Linux)

- **Audio de entrada:** la librería `sounddevice` necesita PortAudio. En Arch:

  ```bash
  sudo pacman -S portaudio
  ```

- **Voz (TTS):** `pyttsx3` usa `espeak`/`espeak-ng`. Selecciona automáticamente voz española si está disponible.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz del proyecto con tu clave:

```
OPENROUTER_API_KEY=sk-or-v1-...
```

## Modelo Vosk

El directorio `model/vosk-model-small-es-0.42` debe contener el modelo **[Vosk small español 0.42](https://alphacephei.com/vosk/models)** descomprimido. La ruta al modelo es relativa al fichero `jarvis_core.py`, así que puedes ejecutar el script desde cualquier carpeta.

## Uso

```bash
python jarvis_core.py
```

- Di tu entrada; JARVYS la transcribe, la añade a `jarvys_diary.txt` y habla una respuesta breve.
- JARVYS recuerda el contexto de toda la sesión para respuestas más coherentes.
- Para terminar, di algo que incluya **salir** o **exit**.

## Estructura

| Archivo / carpeta         | Descripción                                       |
|---------------------------|---------------------------------------------------|
| `jarvis_core.py`          | Lógica principal (STT, diario, OpenRouter, TTS)  |
| `model/vosk-model-.../`   | Modelo de reconocimiento offline                  |
| `jarvys_diary.txt`        | Diario generado (se crea al guardar la 1.ª entrada) |
| `.env`                    | Variables de entorno (no subir al repo)           |

## Seguridad

- **Nunca** subas `OPENROUTER_API_KEY` ni el archivo `.env` al control de versiones. Si alguna clave llegó a commitearse, revócala en OpenRouter y genera otra.
