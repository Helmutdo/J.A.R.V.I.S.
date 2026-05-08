# J.A.R.V.I.S. (JARVYS)

Asistente de diario por voz en español: reconoce lo que dices con **Vosk**, guarda entradas en un archivo de texto y responde con **Gemini** (Google AI).

## Requisitos

- Python 3.10+ recomendado.
- Micrófono y permisos de audio.
- Clave de API de [Google AI Studio](https://aistudio.google.com/apikey) para Gemini.

### Sistema (Linux)

- **Audio de entrada:** la librería `sounddevice` necesita PortAudio. En Arch:

  ```bash
  sudo pacman -S portaudio
  ```

- **Voz (TTS):** `pyttsx3` suele usar el motor disponible en el sistema (por ejemplo `espeak` / `espeak-ng`).

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Define la clave de API (no la guardes en el repositorio):

```bash
export GEMINI_API_KEY="tu_clave_aqui"
```

Opcional: crea un archivo `.env` en la raíz del proyecto y carga las variables con tu shell o herramienta habitual; este proyecto **no** incluye lectura automática de `.env` (solo `GEMINI_API_KEY` en el entorno).

## Modelo Vosk

El directorio `model/vosk-model-small-es-0.42` debe contener el modelo **[Vosk small español 0.42](https://alphacephei.com/vosk/models)** descomprimido. La ruta al modelo es relativa al fichero `jarvys_core.py`, así que puedes ejecutar el script desde cualquier carpeta.

## Uso

```bash
python jarvys_core.py
```

- Di tu entrada; JARVYS la transcribe, la añade a `jarvys_diary.txt` y habla una respuesta breve.
- Para terminar, di algo que incluya **salir** o **exit**.

## Estructura

| Archivo / carpeta        | Descripción                                      |
|--------------------------|--------------------------------------------------|
| `jarvys_core.py`         | Lógica principal (STT, diario, Gemini, TTS)     |
| `model/vosk-model-.../` | Modelo de reconocimiento offline                |
| `jarvys_diary.txt`       | Diario generado (se crea al guardar la 1.ª entrada) |

## Seguridad

- **Nunca** subas `GEMINI_API_KEY` ni un archivo `.env` con secretos al control de versiones. Si alguna clave llegó a commitearse, revócala en la consola de Google y genera otra.
