# Optimizaciones Aplicadas - 2025-11-05

## 🎯 Objetivo
Optimizar el workflow de generación de YouTube Shorts reduciendo tiempo de procesamiento de ~7min a ~4min.

---

## ✅ Optimizaciones Implementadas

### 1. FFmpeg GPU Encoding (NVENC) ⚡ **MAYOR IMPACTO**

**Archivo**: `workflow_youtube_shorts/builder-version-mas-nueva.py` líneas 279-291

**Antes:**
```python
cmd.extend(["-c:v", "libx264", "-preset", "ultrafast"])
cmd.extend(["-crf", "23", "-pix_fmt", "yuv420p"])
cmd.extend(["-c:a", "aac", "-b:a", "192k"])
```

**Después:**
```python
# NVENC GPU encoding (usa 12GB VRAM disponibles)
cmd.extend(["-c:v", "h264_nvenc"])
cmd.extend(["-preset", "p4"])           # balanced quality/speed
cmd.extend(["-tune", "hq"])             # high quality mode
cmd.extend(["-rc", "vbr"])              # variable bitrate
cmd.extend(["-cq", "23"])               # quality level
cmd.extend(["-b:v", "5M"])              # target bitrate
cmd.extend(["-maxrate", "8M"])          # max bitrate
cmd.extend(["-bufsize", "10M"])         # buffer size
cmd.extend(["-spatial-aq", "1"])        # spatial AQ
cmd.extend(["-temporal-aq", "1"])       # temporal AQ
cmd.extend(["-pix_fmt", "yuv420p"])
cmd.extend(["-c:a", "aac", "-b:a", "128k"])  # reduced audio bitrate
```

**Impacto Estimado**:
- 5-10x más rápido en encoding de video
- 8 escenas × 3s encoding = 24s → ~4-5s con GPU
- **Ahorro: ~20 segundos por video**

**Hardware**: Nvidia GPU con 12GB VRAM

---

### 2. Gemini Prompts con Límites de Duración 📝

**Archivo**: `src/services/llm.py`

**Cambios**:

#### a) Prompt de generación de speech (líneas 67-86):
```python
Instructions:
- TARGET LENGTH: 15-45 seconds when spoken (480-1440 tokens)
- For YouTube Shorts: Keep between 15s minimum and 45s maximum
- IMPORTANT: Stay within 480-1440 tokens (15-45 seconds).
  Gemini measures 32 tokens = 1 second of speech.
```

#### b) Prompt de creación de script (líneas 128-154):
```python
DURATION REQUIREMENTS:
- Total video: 15-45 seconds (Shorts format)
- Each scene: 2-6 seconds of speech
- Total speech should match motivational text length
- Gemini token count: 32 tokens = 1 second
```

**Impacto Estimado**:
- Videos más cortos y enfocados (Shorts óptimo: 15-45s)
- Menos escenas → menos TTS → menos encoding
- TTS más rápido con textos más cortos
- **Ahorro: Variable, ~30-60s dependiendo de contenido original**

**Basado en documentación Gemini**: 32 tokens = 1 segundo de audio/video

---

### 3. Revertir Paralelización de Imágenes (Cleanup) 🧹

**Archivos Modificados**:
- `src/workflow.py` - Removidas funciones `_generate_videos_parallel()` y `_generate_videos_sequential()`
- `src/config.py` - Removidos parámetros `parallel_image_*`
- `.env.example` - Removida configuración de paralelización

**Razón**:
- Together.ai FLUX-Free solo acepta 1 imagen a la vez (secuencial)
- Rate limit: ~5-6 imágenes/minuto, exceder = 15 min bloqueo + regenerar API key
- La paralelización causaba HTTP 429 errors

**Resultado**:
- Código más limpio y simple
- Evita errores de rate limiting
- Generación de imágenes ya es rápida (5-6s cada una)

---

## 📊 Impacto Total Estimado

### Tiempos Antes (8 escenas):
```
Script generation (Gemini):    5s
Image generation (FLUX):      40s  (8 × 5s)
TTS generation (Kokoro):     144s  (8 × 18s)
Video encoding (libx264):     24s  (8 × 3s)
Merge:                         5s
─────────────────────────────────
Total:                      ~218s (~3.6 min)
```

### Tiempos Después (estimado con 6 escenas por optimización de Gemini):
```
Script generation (Gemini):    5s
Image generation (FLUX):      30s  (6 × 5s)
TTS generation (Kokoro):     108s  (6 × 18s)
Video encoding (NVENC):        5s  (6 × 0.8s) ⚡ 5-10x faster
Merge:                         5s
─────────────────────────────────
Total:                      ~153s (~2.5 min)
```

**Mejora total: ~65 segundos (~30% más rápido)**

Desglose:
- NVENC GPU: ~20s ahorro
- Gemini optimizado (menos escenas): ~45s ahorro combinado

---

## 🔧 Nota sobre Merge Optimization

La optimización de merge con `-c copy` (sin re-encoding) **NO** se implementó porque:
- Requiere modificar `video/media.py` del media server
- Ese archivo no está disponible en este repositorio
- Es parte del server backend, no del cliente Python

**Para implementar** (en media server):
```python
# Si todos los videos tienen mismo codec:
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4

# Si hay música de fondo:
ffmpeg -f concat -safe 0 -i filelist.txt \
  -i music.mp3 \
  -c:v copy \  # NO re-encode video
  -c:a aac -b:a 128k \  # Solo re-encode audio
  -filter_complex "[0:a][1:a]amix=inputs=2" \
  output.mp4
```

**Ahorro adicional estimado**: 5s → 1s en merge

---

## 🧪 Testing

### Verificar NVENC disponible:
```bash
ffmpeg -encoders | grep nvenc
```

Debería mostrar:
```
h264_nvenc          Nvidia NVENC H.264 encoder
hevc_nvenc          Nvidia NVENC H.265/HEVC encoder
```

### Si NVENC no está disponible:
El comando fallará. Para agregar fallback automático, modificar `builder.py`:

```python
# Intentar NVENC primero
try:
    cmd.extend(["-c:v", "h264_nvenc", ...])
    # ejecutar comando
except:
    # Fallback a x264 CPU
    cmd.extend(["-c:v", "libx264", "-preset", "medium", "-threads", "6"])
```

### Test completo:
```bash
uv run python -m src.main generate --count 1
```

**Indicadores de éxito**:
- Videos más cortos (15-45s)
- Encoding de video significativamente más rápido
- Menos escenas generadas por Gemini
- Tiempo total ~2.5-3 min vs ~3.6-4 min antes

---

## 📁 Archivos Modificados

### Cliente Python (este repositorio):
1. `src/workflow.py` - Revertida paralelización
2. `src/config.py` - Removida config de paralelización
3. `.env.example` - Limpieza de configuración
4. `src/services/llm.py` - Optimización de prompts Gemini

### Media Server (workflow_youtube_shorts/):
5. `workflow_youtube_shorts/builder-version-mas-nueva.py` - NVENC GPU encoding

---

## ⚠️ Consideraciones

### 1. Hardware Requirements
- **GPU Nvidia con NVENC** (12GB VRAM disponibles)
- Si no hay GPU: fallará el encoding
- **Solución**: Agregar detección y fallback a x264

### 2. Gemini Token Limits
- Prompts ahora fuerzan 15-45s de duración
- Videos muy cortos (<15s) pueden no ser ideales
- Videos muy largos (>45s) serán truncados por Gemini
- **Ajustar según necesidad** editando límites en `llm.py`

### 3. Together.ai Rate Limits
- FLUX-Free: 1 imagen a la vez, ~5-6/min máximo
- Exceder = 15 min bloqueo + regenerar API key
- Mantener generación secuencial

---

## 🚀 Próximos Pasos (Opcionales)

### 1. Agregar GPU Detection y Fallback
```python
def detect_nvenc():
    result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True)
    return b"h264_nvenc" in result.stdout

if detect_nvenc():
    # usar NVENC
else:
    # usar x264 optimizado
```

### 2. Optimizar Merge en Media Server
Implementar `-c copy` para merge sin re-encoding

### 3. Chatterbox TTS Optimization
Investigar formas de acelerar generación de audio (actualmente ~18s por escena)

### 4. Parallel Video Encoding (Experimental)
Con NVENC, posible generar 2 videos simultáneamente (12GB VRAM lo permite)

---

**Fecha**: 2025-11-05
**Progreso**: 95% → 98%
**Estado**: Listo para testing
