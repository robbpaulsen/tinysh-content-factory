# Quick Start: Sistema de 2 Fases

Guía rápida para usar el nuevo sistema de upload y calendarización en 2 fases.

## Flujo Básico

```bash
# 1. Generar videos con metadata SEO
python -m src.main generate --count 5

# 2. Subir videos como PRIVATE (Fase 1)
python -m src.main batch-upload

# 3. Calendarizar con metadata final (Fase 2)
python -m src.main batch-schedule
```

## Comandos Principales

### Generar Videos

```bash
# Generar 5 videos
python -m src.main generate --count 5

# Generar con perfil específico
python -m src.main generate --count 5 --profile frank_motivational
```

**Output**:

- `output/video_001.mp4`, `video_002.mp4`, ...
- `output/video_001_metadata.json`, `video_002_metadata.json`, ...

---

### Fase 1: Batch Upload

```bash
# Upload todos los videos (máximo 20)
python -m src.main batch-upload

# Upload solo 5 videos
python -m src.main batch-upload --limit 5

# Upload con logs detallados
python -m src.main --verbose batch-upload
```

**¿Qué hace?**

- Sube videos a YouTube como PRIVATE
- Metadata temporal (será reemplazada en Fase 2)
- Guarda video IDs en `output/video_ids.csv`

**Output**:

```
📤 Phase 1: Batch Upload (Private)

Found 5 videos to upload

Uploading 1/5: video_001.mp4
Upload progress: 100%
✓ Uploaded: dQw4w9WgXcQ

...

✓ Saved 5 video IDs to output/video_ids.csv

Upload Summary:
  ✓ Uploaded: 5
  ✗ Failed: 0

Next step:
  Run: python -m src.main batch-schedule
```

---

### Fase 2: Batch Schedule

```bash
# Preview schedule (recomendado)
python -m src.main batch-schedule --dry-run

# Calendarizar videos
python -m src.main batch-schedule

# Con logs detallados
python -m src.main --verbose batch-schedule
```

**¿Qué hace?**

- Lee `video_ids.csv` y metadata JSON
- Consulta videos ya programados en YouTube
- Calcula siguiente slot disponible (llena huecos)
- Actualiza videos con metadata final + publishAt

**Output (Dry Run)**:

```
📅 Phase 2: Batch Schedule

Found 5 uploaded videos

Checking existing scheduled videos on YouTube...
Found 42 already scheduled videos

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Video          ┃ Video ID     ┃ Publish (Local)   ┃ Publish (UTC)     ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ video_001.mp4  │ dQw4w9WgXcQ  │ 2025-11-27 06:00  │ 2025-11-27 12:00  │
│ video_002.mp4  │ abc123def456 │ 2025-11-27 08:00  │ 2025-11-27 14:00  │
│ video_003.mp4  │ xyz789ghi012 │ 2025-11-27 10:00  │ 2025-11-27 16:00  │
│ video_004.mp4  │ def456ghi789 │ 2025-11-27 12:00  │ 2025-11-27 18:00  │
│ video_005.mp4  │ ghi789jkl012 │ 2025-11-27 14:00  │ 2025-11-27 20:00  │
└────────────────┴──────────────┴───────────────────┴───────────────────┘

🔍 Dry run mode - no videos will be updated
```

**Output (Real)**:

```
Updating videos with metadata and schedule...

Scheduling video_001.mp4 (dQw4w9WgXcQ)...
✓ Scheduled for 2025-11-27 06:00

...

Schedule Summary:
  ✓ Scheduled: 5
  ✗ Failed: 0

Done!
Check YouTube Studio to verify scheduled videos.
```

---

## Verificación

### 1. Verificar archivos generados

```bash
# Listar videos generados
ls -lh output/video_*.mp4

# Verificar metadata
cat output/video_001_metadata.json

# Verificar video IDs
cat output/video_ids.csv
```

### 2. Verificar en YouTube Studio

1. Ir a <https://studio.youtube.com>
2. Navegar a **Content → Videos**
3. Verificar:
   - Status: **Private**
   - Badge: **Scheduled**
   - Publish time: **Correcto**

---

## Casos de Uso Comunes

### Caso 1: Generar y subir contenido diario

```bash
# Día 1: Generar + subir
python -m src.main generate --count 6
python -m src.main batch-upload
python -m src.main batch-schedule

# Día 2: Solo generar nuevos
python -m src.main generate --count 6
# Los videos anteriores ya están programados

# Día 3: Subir videos del día 2
python -m src.main batch-upload
python -m src.main batch-schedule
```

### Caso 2: Generar batch semanal

```bash
# Lunes: Generar 42 videos (7 días × 6 videos/día)
python -m src.main generate --count 42

# Martes: Subir en batches de 20 (límite API)
python -m src.main batch-upload --limit 20
python -m src.main batch-schedule

# Miércoles: Subir resto
python -m src.main batch-upload --limit 20
python -m src.main batch-schedule

# Jueves: Subir últimos
python -m src.main batch-upload
python -m src.main batch-schedule
```

### Caso 3: Error recovery

```bash
# Si falla upload de algunos videos
python -m src.main batch-upload
# → 3/5 uploaded, 2 failed

# Arreglar videos problemáticos
# Volver a intentar (solo subirá los que faltan)
python -m src.main batch-upload

# Si falla scheduling
python -m src.main batch-schedule
# → 3/5 scheduled, 2 failed

# Volver a intentar solo scheduling
python -m src.main batch-schedule
```

---

## Configuración

### Variables importantes en `.env`

```bash
# YouTube Schedule
YOUTUBE_TIMEZONE=America/Mexico_City
YOUTUBE_SCHEDULE_START_HOUR=6   # 6 AM
YOUTUBE_SCHEDULE_END_HOUR=16    # 4 PM
YOUTUBE_SCHEDULE_INTERVAL_HOURS=2

# YouTube Upload
YOUTUBE_PRIVACY_STATUS=private
YOUTUBE_CATEGORY_ID=22  # People & Blogs

# SEO
SEO_ENABLED=true
```

### Slots diarios

Con configuración default:

- **6 AM**, **8 AM**, **10 AM**, **12 PM**, **2 PM**, **4 PM**
- **Total**: 6 videos/día

---

## Troubleshooting Rápido

### Error: "No videos found in output/"

```bash
# Generar videos primero
python -m src.main generate --count 1
```

### Error: "video_ids.csv not found"

```bash
# Ejecutar Fase 1 primero
python -m src.main batch-upload
```

### Videos programados en hora incorrecta

```bash
# Verificar timezone en .env
grep YOUTUBE_TIMEZONE .env

# Debería ser tu timezone local
YOUTUBE_TIMEZONE=America/Chicago
```

### Quiero cancelar un video programado

1. Ir a YouTube Studio
2. Click en el video
3. Click en **Visibility**
4. Cambiar schedule o eliminar video

---

## Límites y Best Practices

✅ **DO**:

- Siempre hacer `--dry-run` antes de `batch-schedule`
- No exceder 20 videos por día
- Hacer backup de `video_ids.csv`
- Verificar en YouTube Studio después de schedule

❌ **DON'T**:

- No borrar `video_ids.csv` antes de schedule
- No subir más de 20 videos/día (límite API)
- No modificar manualmente videos entre fase 1 y 2

---

## Recursos

- [TWO_PHASE_UPLOAD.md](.github/TWO_PHASE_UPLOAD.md) - Documentación completa
- [CHANGELOG.md](.github/CHANGELOG.md) - Historial de cambios
- [README.md](README.md) - Guía general

---

## Cheat Sheet

```bash
# Workflow completo
generate → batch-upload → batch-schedule → verify

# Comandos útiles
python -m src.main --help                    # Ver todos los comandos
python -m src.main batch-upload --help       # Ayuda de batch-upload
python -m src.main batch-schedule --dry-run  # Preview schedule
cat output/video_ids.csv                     # Ver video IDs
ls -lh output/video_*.mp4                    # Listar videos
```
