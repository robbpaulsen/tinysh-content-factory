# Plan de Optimización FFmpeg + Paralelización

## Hardware del Usuario:
- **GPU:** 12GB VRAM Nvidia (NVENC disponible)
- **CPU:** AMD Ryzen 12 cores lógicos (6 físicos)
- **RAM:** 64GB

---

## Problema Actual:

```python
# builder.py línea 280-286
cmd.extend(["-c:v", "libx264", "-preset", "ultrafast"])  # ❌ Subóptimo
cmd.extend(["-crf", "23", "-pix_fmt", "yuv420p"])
cmd.extend(["-c:a", "aac", "-b:a", "192k"])             # ❌ Bitrate alto
```

### Issues:
- ❌ NO usa GPU (Nvidia idle durante encoding)
- ❌ NO usa multithreading (1-2 cores de 12)
- ❌ `ultrafast` = baja compresión = archivos grandes
- ❌ Audio 192k innecesario para Shorts

---

## Solución Propuesta:

### 1. **NVENC GPU Encoding** (RECOMENDADO) 🚀

**Configuración en `.env`:**
```bash
# FFmpeg Optimization
FFMPEG_ENCODER=nvenc               # Opciones: nvenc, x264, auto
FFMPEG_PRESET=p4                   # NVENC: p1-p7 (p4=balanced)
FFMPEG_CQ=23                       # Calidad (18-28, default 23)
FFMPEG_BITRATE=5M                  # Target bitrate
FFMPEG_AUDIO_BITRATE=128k          # Audio bitrate

# Parallelization
PARALLEL_IMAGE_GENERATION=true     # Paralelizar FLUX images
MAX_PARALLEL_IMAGES=8              # Máximo simultáneo
PARALLEL_VIDEO_ENCODING=false      # Experimental (requiere NVENC)
MAX_PARALLEL_VIDEOS=2              # Solo si NVENC activado
```

**Comandos FFmpeg NVENC:**
```python
# Video encoding con GPU
[
    "-c:v", "h264_nvenc",           # GPU encoder
    "-preset", "p4",                 # p1=fastest, p7=slowest/best
    "-tune", "hq",                   # High quality mode
    "-rc", "vbr",                    # Variable bitrate
    "-cq", "23",                     # Quality level
    "-b:v", "5M",                    # Target bitrate
    "-maxrate", "8M",                # Max bitrate
    "-bufsize", "10M",               # Buffer size
    "-spatial-aq", "1",              # Spatial AQ (better quality)
    "-temporal-aq", "1",             # Temporal AQ
    "-pix_fmt", "yuv420p",
]

# Audio optimizado
[
    "-c:a", "aac",
    "-b:a", "128k",                  # Suficiente para Shorts
    "-ar", "44100",
]
```

**Beneficios NVENC:**
- ✅ **5-10x más rápido** (0.5s vs 3s por video)
- ✅ **CPU libre** para TTS y otras tareas
- ✅ **Permite paralelización** de 2-3 videos simultáneos
- ✅ **Menor temperatura** CPU
- ✅ **Calidad comparable** con bitrate adecuado

---

### 2. **x264 CPU Optimizado** (Fallback)

```python
# Software encoding optimizado
[
    "-c:v", "libx264",
    "-preset", "medium",             # Balance (vs ultrafast)
    "-tune", "film",                 # Optimizado para video
    "-crf", "21",                    # Mejor calidad
    "-threads", "6",                 # 6 cores físicos (no 12 lógicos!)
    "-pix_fmt", "yuv420p",
]
```

**Por qué `threads=6` y no 12:**
- Ryzen tiene 6 cores físicos con SMT (Simultaneous Multi-Threading)
- SMT da 12 threads lógicos pero no duplica rendimiento
- FFmpeg x264 escala mejor con cores físicos
- Overhead de coordination con 12 threads > beneficio

---

### 3. **Optimización de Video Merge**

**Si todos los videos tienen mismo codec/formato:**
```python
# Merge sin re-encoding (instantáneo!)
[
    "-c", "copy",                    # Copy streams (no re-encoding)
    "-movflags", "+faststart",       # Optimización web
]
```

**Si necesita agregar música:**
```python
# Solo re-encode audio, video copy
[
    "-c:v", "copy",                  # Video copy (rápido)
    "-c:a", "aac",                   # Re-encode audio con música
    "-b:a", "128k",
    "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest:weights=1 0.2"
]
```

---

### 4. **Estrategia de Paralelización**

```
WORKFLOW OPTIMIZADO:

1. Gemini genera script                    [5s]

2. 🚀 PARALELO: Imágenes (8 simultáneas)  [10s]
   ├─ Image 1 (FLUX API)
   ├─ Image 2 (FLUX API)
   ├─ ... (rate limiting 6/min)
   └─ Image 8 (FLUX API)

3. ⏱️ SECUENCIAL: TTS (una a la vez)      [144s]
   ├─ TTS 1 (18s) [Poll cada 15s]
   ├─ TTS 2 (18s) [Poll cada 15s]
   └─ ...

4a. CON NVENC 🚀: Videos paralelos         [8s]
    ├─ Video 1+2 simultáneos (GPU)
    ├─ Video 3+4 simultáneos (GPU)
    └─ ... (2 a la vez)

4b. SIN NVENC ⏱️: Videos secuenciales     [24s]
    └─ Video por video (CPU)

5. ⏱️ MERGE con copy                       [1s]
   └─ Concatenación sin re-encode
```

---

## Comparación de Tiempos (8 escenas):

| Configuración | Imágenes | TTS | Videos | Merge | **TOTAL** |
|---------------|----------|-----|--------|-------|-----------|
| **Actual** | 40s | 144s | 24s | 5s | **213s** (~3.5min) |
| **Solo imgs paralelas** | 10s | 144s | 24s | 5s | **183s** (~3min) |
| **Imgs + NVENC** | 10s | 144s | 8s | 1s | **163s** (~2.7min) |
| **Full optimizado** | 10s | 144s | 4s* | 1s | **159s** (~2.6min)** |

\* = Videos paralelos con NVENC (2 simultáneos)
** = **25% más rápido** que actual

---

## Riesgos y Consideraciones:

### ✅ Bajo Riesgo (RECOMENDADO):
- Paralelizar imágenes (API externa)
- Usar NVENC (GPU idle)
- Optimizar presets FFmpeg
- Merge con copy

### ⚠️ Medio Riesgo:
- Paralelizar 2 videos con NVENC
  - Requiere testing
  - Monitorear VRAM usage
  - 12GB suficiente para 2-3 streams

### ❌ Alto Riesgo (NO HACER):
- Paralelizar TTS (RAM/CPU intensivo)
- Más de 3 videos paralelos con NVENC
- Usar todos los 12 threads lógicos en x264

---

## Implementación:

### Fase 1: Config + Imágenes Paralelas
- Agregar settings en `.env`
- Implementar paralelización de imágenes
- Testing: Sin riesgo

### Fase 2: Optimizar FFmpeg
- Detectar NVENC disponible
- Aplicar preset optimizado
- Testing: Comparar calidad

### Fase 3: Videos Paralelos (Opcional)
- Solo si NVENC funciona bien
- Máximo 2 simultáneos
- Monitorear VRAM

---

## Testing Checklist:

- [ ] Verificar NVENC disponible: `ffmpeg -encoders | grep nvenc`
- [ ] Test 1 video con NVENC: Velocidad + calidad
- [ ] Test imágenes paralelas: Rate limiting OK
- [ ] Test 2 videos paralelos: VRAM usage
- [ ] Comparar tamaño de archivos finales
- [ ] Validar calidad visual en YouTube

---

## Notas Adicionales:

### ¿Por qué NO paralelizar TTS?

Como tu experiencia con ComfyUI:
```
TTS carga modelo en RAM (~2-4GB)
3 TTS paralelos = 12GB RAM ocupados
                + CPU contention
                + Context switching overhead
                = MÁS LENTO que secuencial
```

### ¿2 videos NVENC simultáneos es safe?

Sí, con 12GB VRAM:
```
1 stream h264_nvenc = ~500MB-1GB VRAM
2 streams          = ~2GB VRAM total
Sobran             = 10GB para el modelo base

SAFE ✅
```

3+ streams = Posible pero arriesgado (puede degradar performance)

---

## Comando FFmpeg Ejemplo Completo:

### Generación de Video con NVENC:
```bash
ffmpeg -y \
  -loop 1 -t 18.5 -i image.jpg \
  -i audio.wav \
  -filter_complex "[0]scale=768:1344,setsar=1:1,crop=768:1344,zoompan=z='zoom+0.001':x=0:y=0:d=464:s=768x1344:fps=25[bg];[bg]subtitles=captions.ass[v]" \
  -map "[v]" -map 1:a \
  -c:v h264_nvenc -preset p4 -tune hq -rc vbr -cq 23 -b:v 5M -maxrate 8M -bufsize 10M \
  -c:a aac -b:a 128k -ar 44100 \
  -pix_fmt yuv420p \
  -t 18.5 \
  output.mp4
```

### Merge con Copy:
```bash
ffmpeg -y \
  -f concat -safe 0 -i filelist.txt \
  -i background_music.mp3 \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=longest:weights=1 0.1[aout]" \
  -map 0:v -c:v copy \
  -map "[aout]" -c:a aac -b:a 128k \
  -movflags +faststart \
  output_final.mp4
```

---

¿Proceder con implementación?
