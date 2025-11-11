# Feature 3: Uso de Media Local vs Docker

Comparación de cómo se ejecuta actualmente (Docker) vs cómo funcionaría con procesamiento local.

---

## 📊 Flujo Actual (Docker)

### Arquitectura:
```
Python Client (src/) → HTTP → Docker Container (server-code-and-layout/)
```

### Ejemplo de uso actual:

```python
# src/workflow.py
from src.services.media import MediaService

# 1. Conectar al servidor Docker
media = MediaService(base_url="http://localhost:8000")
await media.health_check()  # ¿Está el Docker corriendo?

# 2. Generar TTS (envía HTTP request)
voice_config = {
    "engine": "chatterbox",
    "sample_path": "/samples/voice.mp3",
    "temperature": 0.8,
    "cfg_weight": 0.65,
    "exaggeration": 0.55
}
tts = await media.generate_tts("Hello world", voice_config=voice_config)
# → POST http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox
# → Espera respuesta con file_id
# → file_id = "audio_abc123.wav"

# 3. Generar video (envía HTTP request)
video = await media.generate_captioned_video(
    image_id="image_xyz.jpg",
    tts_id="audio_abc123.wav",
    text="Hello world"
)
# → POST http://localhost:8000/api/v1/media/video-tools/captioned-video
# → Espera respuesta con file_id
# → file_id = "video_def456.mp4"

# 4. Merge videos (envía HTTP request)
final_video_id = await media.merge_videos(
    ["video_def456.mp4", "video_ghi789.mp4"],
    background_music_path="music.mp3",
    music_volume=0.1
)
# → POST http://localhost:8000/api/v1/media/video-tools/merge
# → Espera respuesta con file_id
# → file_id = "final_jkl012.mp4"

# 5. Descargar archivo (HTTP download)
await media.download_file(final_video_id, "./output/video.mp4")
```

**Overhead actual:**
- ❌ HTTP requests/responses para cada operación
- ❌ Serialización JSON
- ❌ Upload/download de archivos
- ❌ Container debe estar corriendo (Docker)
- ❌ Debugging indirecto (logs en container)
- ❌ Reiniciar container para cambios de código

---

## 🚀 Flujo Futuro (Local)

### Arquitectura:
```
Python Client (src/) → Direct calls → src/media_local/
```

### Ejemplo de uso futuro (lo que falta implementar):

```python
# OPCIÓN 1: Uso directo (sin MediaService)
from src.media_local import ChatterboxTTS, VideoBuilder, StorageManager
from src.media_local.ffmpeg import MediaUtils

# 1. No hay health check - es código local
# (Si falta torch o chatterbox, fallará en import con error claro)

# 2. Generar TTS (llamada directa Python)
tts = ChatterboxTTS()
success = tts.generate(
    text="Hello world",
    output_path="./temp/audio.wav",
    sample_audio_path="./samples/voice.mp3",
    temperature=0.8,
    cfg_weight=0.65,
    exaggeration=0.55
)
# → Ejecución directa en Python
# → No HTTP, no container
# → output_path = "./temp/audio.wav"

# 3. Generar video (llamada directa Python)
media_utils = MediaUtils()
builder = VideoBuilder(dimensions=(1080, 1920))
builder.set_media_utils(media_utils)
builder.set_background_image("./temp/image.jpg")
builder.set_audio("./temp/audio.wav")
builder.set_captions("./temp/captions.srt")
builder.set_output_path("./temp/video.mp4")
success = builder.execute()
# → Ejecución FFmpeg directa
# → No HTTP, no container
# → output_path = "./temp/video.mp4"

# 4. Merge videos (llamada directa Python)
media_utils = MediaUtils()
success = media_utils.merge_videos(
    video_paths=["./temp/video1.mp4", "./temp/video2.mp4"],
    output_path="./output/final.mp4",
    background_music_path="./music/track.mp3",
    background_music_volume=0.1
)
# → Ejecución FFmpeg directa
# → No HTTP, no container
# → output_path = "./output/final.mp4"

# 5. No hay download - los archivos ya están localmente
# ✅ ./output/final.mp4 ya existe
```

**OPCIÓN 2: Uso a través de MediaService actualizado (mejor para mantener compatibilidad)**

```python
# src/services/media.py (modificado)
from src.media_local import ChatterboxTTS, VideoBuilder
from src.media_local.ffmpeg import MediaUtils

class MediaService:
    def __init__(self, use_local: bool = True):
        """
        Args:
            use_local: Si True, usa procesamiento local.
                      Si False, usa Docker (fallback).
        """
        self.use_local = use_local

        if use_local:
            # Inicializar procesadores locales
            self.chatterbox = ChatterboxTTS()
            self.media_utils = MediaUtils()
        else:
            # Usar Docker (código actual)
            self.base_url = settings.media_server_url
            self.client = httpx.AsyncClient(...)

    async def generate_tts(self, text: str, voice_config: dict | None = None):
        if self.use_local:
            # Procesamiento local (nuevo)
            output_path = f"./temp/audio_{uuid4()}.wav"
            success = self.chatterbox.generate(
                text=text,
                output_path=output_path,
                sample_audio_path=voice_config.get("sample_path"),
                temperature=voice_config.get("temperature", 0.8),
                cfg_weight=voice_config.get("cfg_weight", 0.5),
                exaggeration=voice_config.get("exaggeration", 0.5)
            )
            return GeneratedTTS(file_id=output_path, duration=None)
        else:
            # Docker (actual)
            file_id = await self.generate_tts_direct(text, voice_config)
            return GeneratedTTS(file_id=file_id, duration=None)
```

**Beneficios:**
- ✅ No HTTP overhead
- ✅ Ejecución directa Python
- ✅ Debugging fácil (breakpoints directos)
- ✅ No Docker necesario
- ✅ Modificar código sin reiniciar nada
- ✅ Logs integrados con loguru

---

## 🔧 Estado Actual de Implementación

### ✅ Implementado (Tasks 3.1-3.4):
```python
# Ya disponible:
from src.media_local.config import device, get_device_info
from src.media_local.tts import ChatterboxTTS
from src.media_local.ffmpeg import MediaUtils

# Device detection
print(device)  # cuda, mps, o cpu
print(get_device_info())  # Info detallada

# TTS directo
tts = ChatterboxTTS()
tts.generate(
    text="Hello world",
    output_path="./test.wav",
    sample_audio_path="./voice_sample.mp3"
)

# FFmpeg directo
utils = MediaUtils()
audio_info = utils.get_audio_info("./test.wav")
print(audio_info)  # {'duration': 2.5, 'sample_rate': '24000', ...}

utils.merge_videos(
    video_paths=["./video1.mp4", "./video2.mp4"],
    output_path="./merged.mp4",
    background_music_path="./music.mp3",
    background_music_volume=0.1
)
```

### ⏸️ Pendiente (Tasks 3.5-3.9):

**Task 3.5 - VideoBuilder:**
```python
# FALTA IMPLEMENTAR:
from src.media_local.video import VideoBuilder

builder = VideoBuilder(dimensions=(1080, 1920))
builder.set_background_image("./image.jpg")
builder.set_audio("./audio.wav")
builder.set_captions("./captions.srt")
builder.set_output_path("./video.mp4")
builder.execute()
```

**Task 3.6 - Storage Manager:**
```python
# FALTA IMPLEMENTAR:
from src.media_local.storage import StorageManager

storage = StorageManager(temp_dir="./temp", output_dir="./output")
temp_file = storage.create_temp_file(suffix=".wav")
storage.cleanup_old_files(max_age_minutes=30)
```

**Task 3.7 - Fallback System:**
```python
# FALTA IMPLEMENTAR:
from src.services.media import MediaService

# Auto-detecta si local processing disponible
media = MediaService(use_local="auto")  # intenta local, fallback a Docker
```

**Task 3.8 - Testing:**
```bash
# FALTA IMPLEMENTAR:
uv run python -m pytest tests/test_media_local.py
```

---

## 🎯 Próximos Pasos

Para completar la migración necesitamos:

1. **VideoBuilder** - Construir videos desde image + audio + captions
2. **Storage Manager** - Gestión de archivos temporales
3. **Integrar en MediaService** - Hacer que `src/services/media.py` use local primero
4. **Fallback Docker** - Si local falla, usar Docker automáticamente
5. **Testing** - Probar con archivos reales

¿Quieres que continúe con VideoBuilder (Task 3.5) o prefieres hacer testing primero de lo que ya está?
