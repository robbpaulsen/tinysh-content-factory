# Sistema de Upload y Calendarización en 2 Fases

Este documento explica el nuevo sistema de upload y calendarización de videos a YouTube en 2 fases separadas.

## Resumen

El sistema separa el proceso de subida y calendarización en dos fases independientes:

**Fase 1 (Upload)**: Sube videos a YouTube como PRIVATE con metadata temporal → guarda video IDs
**Fase 2 (Schedule)**: Actualiza videos con metadata final + calendariza publish times

### Ventajas

- ✅ **Resiliencia**: Si falla una fase, puedes reintentar sin repetir la otra
- ✅ **Flexibilidad**: Puedes subir videos ahora y calendarizarlos después
- ✅ **Fill Gaps**: Calendarización inteligente que llena huecos en el schedule existente
- ✅ **Límites API**: Respeta límite de 20 videos/día de YouTube API

## Flujo Completo

```
1. Generar videos con metadata SEO
   ↓
   python -m src.main generate --count 5

2. Upload videos como PRIVATE (Fase 1)
   ↓
   python -m src.main batch-upload

3. Calendarizar con metadata final (Fase 2)
   ↓
   python -m src.main batch-schedule
```

## Fase 1: Batch Upload

### Comando

```bash
# Upload todos los videos (máximo 20 por día)
python -m src.main batch-upload

# Upload solo 5 videos
python -m src.main batch-upload --limit 5
```

### ¿Qué hace?

1. Busca todos los archivos `video_*.mp4` en `output/`
2. Sube cada video a YouTube como PRIVATE con metadata temporal
3. Guarda video IDs en `output/video_ids.csv`

### Output

**Archivo generado**: `output/video_ids.csv`

```csv
filename,video_id
video_001.mp4,dQw4w9WgXcQ
video_002.mp4,abc123def456
video_003.mp4,xyz789ghi012
```

### Metadata Temporal

Los videos se suben con metadata temporal que será reemplazada en Fase 2:

- **Title**: "Uploading... (metadata pending)"
- **Description**: "This video is being processed. Metadata will be updated shortly."
- **Privacy**: Private
- **Category**: People & Blogs (22)

### Límites

- **Máximo**: 20 videos por día (límite de YouTube API)
- **Quota**: ~1600 unidades por video = ~20 videos con quota default de 10,000

## Fase 2: Batch Schedule

### Comando

```bash
# Preview del schedule (dry-run)
python -m src.main batch-schedule --dry-run

# Calendarizar videos
python -m src.main batch-schedule
```

### ¿Qué hace?

1. Lee `output/video_ids.csv` (generado en Fase 1)
2. Lee archivos `output/video_XXX_metadata.json` (generados con los videos)
3. **Consulta YouTube API** para ver videos ya programados
4. **Calcula siguiente slot disponible** usando lógica de "fill gaps"
5. Actualiza cada video con:
   - Metadata final (title, description, tags)
   - Scheduled publish time (publishAt)

### Lógica de "Fill Gaps"

El scheduler es inteligente y llena huecos en el schedule existente:

#### Escenario 1: Hay slots disponibles hoy

```
Videos programados hoy:
  - 06:00 AM ✓
  - 08:00 AM ✓
  - 10:00 AM ✓

Siguiente slot: 12:00 PM (llena el hueco)
```

#### Escenario 2: Hoy está lleno

```
Videos programados hoy:
  - 06:00 AM ✓
  - 08:00 AM ✓
  - 10:00 AM ✓
  - 12:00 PM ✓
  - 02:00 PM ✓
  - 04:00 PM ✓ (último slot)

Siguiente slot: Mañana 06:00 AM
```

#### Escenario 3: Hay gaps entre días

```
Día 1:
  - 06:00 AM ✓
  - 08:00 AM ✓
  - 10:00 AM ✗ (GAP)
  - 12:00 PM ✓

Siguiente slot: Día 1, 10:00 AM (llena el gap)
```

### Horario de Publicación

Configurado en `.env`:

```bash
YOUTUBE_TIMEZONE=America/Chicago
YOUTUBE_SCHEDULE_START_HOUR=6   # 6 AM
YOUTUBE_SCHEDULE_END_HOUR=16    # 4 PM
YOUTUBE_SCHEDULE_INTERVAL_HOURS=2
```

**Slots diarios**: 6 AM, 8 AM, 10 AM, 12 PM, 2 PM, 4 PM = **6 videos/día**

### Output

**Consola muestra tabla**:

```
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Video          ┃ Video ID     ┃ Publish (Local)   ┃ Publish (UTC)     ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ video_001.mp4  │ dQw4w9WgXcQ  │ 2025-11-14 06:00  │ 2025-11-14 12:00  │
│ video_002.mp4  │ abc123def456 │ 2025-11-14 08:00  │ 2025-11-14 14:00  │
│ video_003.mp4  │ xyz789ghi012 │ 2025-11-14 10:00  │ 2025-11-14 16:00  │
└────────────────┴──────────────┴───────────────────┴───────────────────┘
```

## Ejemplo Completo

### Paso 1: Generar contenido

```bash
python -m src.main generate --count 3
```

**Output**:
```
output/
├── video_001.mp4
├── video_001_metadata.json
├── video_002.mp4
├── video_002_metadata.json
├── video_003.mp4
└── video_003_metadata.json
```

### Paso 2: Upload videos (Fase 1)

```bash
python -m src.main batch-upload
```

**Output**:
```
📤 Phase 1: Batch Upload (Private)

Found 3 videos to upload

Uploading 1/3: video_001.mp4
Upload progress: 100%
✓ Uploaded: dQw4w9WgXcQ

Uploading 2/3: video_002.mp4
Upload progress: 100%
✓ Uploaded: abc123def456

Uploading 3/3: video_003.mp4
Upload progress: 100%
✓ Uploaded: xyz789ghi012

✓ Saved 3 video IDs to output/video_ids.csv

Upload Summary:
  ✓ Uploaded: 3
  ✗ Failed: 0

Next step:
  Run: python -m src.main batch-schedule
```

**Archivo generado**: `output/video_ids.csv`

### Paso 3: Preview schedule (Fase 2 - Dry Run)

```bash
python -m src.main batch-schedule --dry-run
```

**Output**:
```
📅 Phase 2: Batch Schedule

Found 3 uploaded videos

Checking existing scheduled videos on YouTube...
Found 42 already scheduled videos

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Video          ┃ Video ID     ┃ Publish (Local)   ┃ Publish (UTC)     ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ video_001.mp4  │ dQw4w9WgXcQ  │ 2025-11-27 06:00  │ 2025-11-27 12:00  │
│ video_002.mp4  │ abc123def456 │ 2025-11-27 08:00  │ 2025-11-27 14:00  │
│ video_003.mp4  │ xyz789ghi012 │ 2025-11-27 10:00  │ 2025-11-27 16:00  │
└────────────────┴──────────────┴───────────────────┴───────────────────┘

🔍 Dry run mode - no videos will be updated
```

### Paso 4: Calendarizar (Fase 2 - Real)

```bash
python -m src.main batch-schedule
```

**Output**:
```
📅 Phase 2: Batch Schedule

Found 3 uploaded videos

Checking existing scheduled videos on YouTube...
Found 42 already scheduled videos

[Tabla con schedule]

Updating videos with metadata and schedule...

Scheduling video_001.mp4 (dQw4w9WgXcQ)...
✓ Scheduled for 2025-11-27 06:00

Scheduling video_002.mp4 (abc123def456)...
✓ Scheduled for 2025-11-27 08:00

Scheduling video_003.mp4 (xyz789ghi012)...
✓ Scheduled for 2025-11-27 10:00

Schedule Summary:
  ✓ Scheduled: 3
  ✗ Failed: 0

Done!
Check YouTube Studio to verify scheduled videos.
```

## Verificación en YouTube Studio

1. Ir a https://studio.youtube.com
2. Navegar a **Content → Videos**
3. Verificar que los videos tienen:
   - Status: **Private**
   - Badge: **Scheduled**
   - Publish time: **Correcto**
4. Click en video para ver metadata completa:
   - Title optimizado con SEO
   - Description con hashtags
   - Tags relevantes
   - Category: People & Blogs

## Recuperación de Errores

### Error en Fase 1 (Upload)

Si algunos videos fallan al subir:

1. Revisa los errores en consola
2. Elimina videos problemáticos o arregla el problema
3. Vuelve a ejecutar `batch-upload`
4. Los videos exitosos NO se volverán a subir (verifica `video_ids.csv`)

### Error en Fase 2 (Schedule)

Si algunos videos fallan al calendarizar:

1. Revisa los errores en consola
2. Arregla metadata JSON si es necesario
3. Vuelve a ejecutar `batch-schedule`
4. Solo los videos que fallaron se volverán a intentar

## Límites y Consideraciones

### Límites de YouTube API

- **Upload quota**: ~1,600 unidades por video
- **Update quota**: ~50 unidades por video
- **Daily quota default**: 10,000 unidades
- **Videos por día**: ~20 videos (upload + schedule)

### Límites del Sistema

- **Max videos programados**: 100 por canal (límite de YouTube)
- **Batch size recomendado**: 20 videos por día
- **Timezone**: Configurable en .env

### Best Practices

1. **Siempre hacer dry-run primero**:
   ```bash
   python -m src.main batch-schedule --dry-run
   ```

2. **No exceder 20 videos/día**:
   ```bash
   python -m src.main batch-upload --limit 20
   ```

3. **Verificar video_ids.csv** antes de schedule:
   ```bash
   cat output/video_ids.csv
   ```

4. **Backup de video_ids.csv** después de upload:
   ```bash
   cp output/video_ids.csv output/video_ids_backup_$(date +%Y%m%d).csv
   ```

## Estructura de Archivos

```
output/
├── video_001.mp4              # Video generado
├── video_001_metadata.json    # Metadata SEO
├── video_002.mp4
├── video_002_metadata.json
├── video_003.mp4
├── video_003_metadata.json
├── video_ids.csv              # Generado en Fase 1
└── logs/                      # Logs del sistema
    └── youtube_shorts_YYYYMMDD_HHMMSS.log
```

### Ejemplo de video_ids.csv

```csv
filename,video_id
video_001.mp4,dQw4w9WgXcQ
video_002.mp4,abc123def456
video_003.mp4,xyz789ghi012
```

### Ejemplo de metadata.json

```json
{
  "title": "5 Habits That Changed My Life Forever",
  "description": "Discover powerful habits for transformation...\n\n#motivation #shorts #selfimprovement",
  "tags": ["motivation", "self improvement", "productivity", "mindset", "success"],
  "category_id": "22",
  "original_title": "Transform Your Life with These Habits",
  "original_description": "A motivational story about...",
  "profile": "frank_motivational"
}
```

## Troubleshooting

### Video no aparece en YouTube Studio

- Espera 1-2 minutos para procesamiento
- Refresca la página
- Verifica que el upload fue exitoso (check video_ids.csv)

### Schedule no se aplicó

- Verifica que ejecutaste Fase 2 (batch-schedule)
- Verifica que no hubo errores en consola
- Verifica timezone en .env

### Videos programados en hora incorrecta

- Verifica `YOUTUBE_TIMEZONE` en `.env`
- Recuerda que YouTube API usa UTC internamente
- El sistema convierte automáticamente tu timezone a UTC

### Gaps no se llenan correctamente

- Verifica que el scheduler detectó videos existentes
- Revisa logs para ver qué slots calculó
- Usa `--dry-run` para preview antes de ejecutar

## Comparación con Sistema Anterior

| Feature | Sistema Anterior (1 fase) | Sistema Nuevo (2 fases) |
|---------|---------------------------|-------------------------|
| Upload + Schedule | Simultáneo | Separado |
| Recuperación de errores | Difícil | Fácil (por fase) |
| Fill gaps | No | Sí |
| Flexibilidad | Baja | Alta |
| API calls | Más eficiente | Más robusto |
| Complejidad | Simple | Moderada |

## Código Relevante

### YouTubeService Methods

- `upload_video_as_private()` - Fase 1
- `get_scheduled_videos()` - Consulta videos programados
- `update_video_schedule()` - Fase 2

### VideoScheduler Methods

- `calculate_next_available_slot()` - Lógica de "fill gaps"
- `calculate_schedule()` - Schedule tradicional (batch completo)

### CLI Commands

- `batch-upload` - Fase 1
- `batch-schedule` - Fase 2
- `schedule-uploads` - Sistema anterior (1 fase, aún disponible)

---

**Documentos relacionados**:
- [BATCH_SCHEDULING.md](BATCH_SCHEDULING.md) - Sistema anterior (1 fase)
- [YOUTUBE_SCHEDULING.md](YOUTUBE_SCHEDULING.md) - Detalles de YouTube API
- [README.md](../README.md) - Guía general de uso
