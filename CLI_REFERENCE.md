# CLI Reference - YouTube Shorts Factory

Referencia completa de todos los comandos CLI disponibles.

## Tabla de Contenidos

- [Comandos Generales](#comandos-generales)
- [Comandos de Canal](#comandos-de-canal)
- [Comandos de Generación](#comandos-de-generación)
- [Comandos de YouTube](#comandos-de-youtube)
- [Opciones Globales](#opciones-globales)

---

## Comandos Generales

### `--help`

Muestra ayuda general o de un comando específico.

```bash
# Ayuda general
python -m src.main --help

# Ayuda de un comando específico
python -m src.main generate --help
```

### `--version`

Muestra la versión del CLI.

```bash
python -m src.main --version
```

**Output:**
```
YouTube Shorts Factory, version 0.1.0
```

### `--verbose` / `-v`

Activa modo verbose (logging detallado).

```bash
# Con verbose
python -m src.main --verbose generate --count 1

# Forma corta
python -m src.main -v generate --count 1
```

**Qué hace:**
- ✅ DEBUG level logging
- ✅ Guarda logs en `output/logs/`
- ✅ Muestra tiempos de cada operación
- ✅ Stack traces completos en errores

---

## Comandos de Canal

### `list-channels`

Lista todos los canales configurados.

```bash
python -m src.main list-channels
```

**Output:**
```
📺 Available Channels

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Channel          ┃ Name            ┃ Type                ┃ Handle            ┃ Format         ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ momentum_mindset │ Momentum...     │ Ai Generated Shorts │ @MomentumMindset  │ 9:16 (shorts)  │
│ wealth_wisdom    │ Wealth Wisdom   │ Ai Generated Shorts │ @WealthWisdom     │ 9:16 (shorts)  │
│ finance_wins     │ Finance Wins    │ Youtube Compilation │ @FinanceWins      │ 16:9 (compila) │
└──────────────────┴─────────────────┴─────────────────────┴───────────────────┴────────────────┘
```

**Qué muestra:**
- Nombre interno del canal (`momentum_mindset`)
- Nombre público (`Momentum Mindset`)
- Tipo de canal (`ai_generated_shorts`, `ai_generated_videos`, `youtube_compilation`)
- Handle de YouTube (`@MomentumMindset`)
- Formato de video (`9:16 shorts`, `16:9 compilation`)

---

## Comandos de Configuración

### `init`

Crea archivo `.env` desde el template `.env.example`.

```bash
python -m src.main init
```

**Qué hace:**
- ✅ Copia `.env.example` → `.env`
- ✅ Muestra siguientes pasos
- ⚠️ Pregunta antes de sobreescribir si `.env` ya existe

**Output:**
```
✓ Created .env file

Next steps:
1. Edit .env and add your API keys
2. Place your Google credentials.json in the project root
3. Run: python -m src.main validate-config
4. Run: python -m src.main check-server
5. Run: python -m src.main generate --count 1
```

### `validate-config`

Valida la configuración en `.env`.

```bash
python -m src.main validate-config
```

**Qué verifica:**
- ✅ `GOOGLE_API_KEY` está configurada
- ✅ `TOGETHER_API_KEY` está configurada
- ✅ `credentials.json` existe
- ⚠️ Background music (opcional)
- ⚠️ Chatterbox voice sample (opcional)

**Output exitoso:**
```
Configuration Validation

✓ Google API Key configured
✓ Together.ai API Key configured
✓ Google credentials file found

⚠ Warnings:
  • Background music not configured (optional)
  • Chatterbox voice sample not configured (using default voice)

✓ Configuration is valid!
```

### `check-server`

Verifica que el media server esté funcionando.

```bash
python -m src.main check-server
```

**Qué hace:**
- ✅ Hace request a `{MEDIA_SERVER_URL}/health`
- ✅ Verifica que responda correctamente

**Output exitoso:**
```
✓ Media server is ready!
```

**Output de error:**
```
✗ Media server check failed: Connection refused
```

---

## Comandos de Generación

### `update-stories`

Descarga stories de Reddit y las guarda en Google Sheets.

```bash
# Usando subreddit configurado en .env
python -m src.main update-stories

# Subreddit personalizado
python -m src.main update-stories --subreddit getdisciplined

# Con límite de stories
python -m src.main update-stories --subreddit selfimprovement --limit 50
```

**Opciones:**

| Opción | Alias | Tipo | Default | Descripción |
|--------|-------|------|---------|-------------|
| `--subreddit` | `-s` | string | `.env` | Subreddit a scrapear |
| `--limit` | `-l` | int | 25 | Número de stories a descargar |

**Output:**
```
📥 Fetching stories from Reddit...
✓ Saved 25 stories to Google Sheets
```

### `generate`

Genera videos desde stories en Google Sheets.

```bash
# Generar 1 video para un canal específico
python -m src.main generate --channel momentum_mindset --count 1

# Generar 6 videos y actualizar Reddit primero
python -m src.main generate --channel wealth_wisdom --count 6 --update

# Usar perfil de voz específico
python -m src.main generate --channel momentum_mindset --count 1 --profile brody_calm

# Sin especificar canal (usa el primero disponible)
python -m src.main generate --count 1
```

**Opciones:**

| Opción | Alias | Tipo | Default | Descripción |
|--------|-------|------|---------|-------------|
| `--channel` | | string | primero | Canal a usar |
| `--count` | `-c` | int | 1 | Número de videos a generar |
| `--update` | | bool | false | Actualizar stories de Reddit primero |
| `--no-update` | | bool | true | No actualizar stories |
| `--profile` | `-p` | string | default | Perfil de voz/música a usar |

**Qué hace:**
1. Selecciona story sin video de Google Sheets
2. Genera script con Gemini
3. Genera imágenes con FLUX
4. Genera audio con TTS (Kokoro/Chatterbox)
5. Crea videos con captions
6. Merge videos + música
7. Guarda en `channels/{channel}/output/`
8. Actualiza Google Sheets con video ID

**Output:**
```
🚀 Starting YouTube Shorts Factory

Checking media server...
✓ Media server is ready

🎬 Processing story: Transform Your Life with These 5 Habits...
  → Creating script with Gemini...
  ✓ Script created with 5 scenes
  → Processing 5 scenes...
  Scene 1/5...
  ✓ Generated 5 scene videos
  → Merging videos...
  ✓ Videos merged with music: Track Name
  → Downloading video...
  ✓ Video saved to channels/momentum_mindset/output/video_001.mp4
  → Generating SEO metadata...
  ✓ SEO metadata saved to video_001_metadata.json
✓ Updated Google Sheets row 15

🎉 Video complete: channels/momentum_mindset/output/video_001.mp4
```

### `generate-single`

Genera video de una historia específica de Reddit por ID.

```bash
# Por ID de Reddit
python -m src.main generate-single abc123xyz

# Con canal específico
python -m src.main generate-single abc123xyz --channel momentum_mindset

# Con perfil específico
python -m src.main generate-single abc123xyz --profile denzel_powerful
```

**Argumentos:**

| Argumento | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `story_id` | string | ✅ | Reddit post ID (e.g., 'abc123xyz') |

**Opciones:**

| Opción | Alias | Tipo | Default | Descripción |
|--------|-------|------|---------|-------------|
| `--profile` | `-p` | string | default | Perfil de voz/música a usar |

**Útil para:**
- Generar video de un post específico que viste en Reddit
- Testear con contenido conocido
- Regenerar video si algo falló

### `batch-all`

Procesa todos los canales automáticamente en secuencia.

```bash
# Generar 3 videos para cada canal AI
python -m src.main batch-all --count 3

# Generar y actualizar Reddit primero
python -m src.main batch-all --count 5 --update
```

**Opciones:**

| Opción | Alias | Tipo | Default | Descripción |
|--------|-------|------|---------|-------------|
| `--count` | `-c` | int | 1 | Videos por canal AI |
| `--update` | | bool | false | Actualizar stories primero |
| `--no-update` | | bool | true | No actualizar stories |

**Qué hace:**
1. Lista todos los canales disponibles
2. Para cada canal:
   - Si es `ai_generated_*`: Genera {count} videos
   - Si es `youtube_compilation`: Skipped (por ahora)
3. Muestra tabla de resumen al final

**Output:**
```
🚀 Batch Processing All Channels

Found 3 channels to process

═══ Channel 1/3: momentum_mindset ═══

Channel type: Ai Generated Shorts
[... proceso de generación ...]
✓ Video complete

═══ Channel 2/3: wealth_wisdom ═══

Channel type: Ai Generated Shorts
[... proceso de generación ...]
✓ Video complete

═══ Channel 3/3: finance_wins ═══

Channel type: Youtube Compilation
⚠ Compilation channels not yet implemented in batch-all
Use manual workflow for now

═══════════════════════════════════════════════
Batch Processing Summary

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Channel          ┃ Status    ┃ Details                ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ momentum_mindset │ ✓ Success │ 3 videos generated     │
│ wealth_wisdom    │ ✓ Success │ 3 videos generated     │
│ finance_wins     │ ⊘ Skipped │ compilation not impl.  │
└──────────────────┴───────────┴────────────────────────┘

✓ Successful: 2
✗ Failed: 0
⊘ Skipped: 1
```

---

## Comandos de YouTube

### `batch-upload`

**Fase 1**: Sube videos a YouTube como PRIVADOS con metadata temporal.

```bash
# Subir todos los videos de un canal (max 20/día)
python -m src.main batch-upload --channel momentum_mindset

# Limitar a 5 videos
python -m src.main batch-upload --channel wealth_wisdom --limit 5

# Sin especificar canal (usa el primero)
python -m src.main batch-upload
```

**Opciones:**

| Opción | Alias | Tipo | Default | Descripción |
|--------|-------|------|---------|-------------|
| `--channel` | | string | primero | Canal a usar |
| `--limit` | `-l` | int | 20 | Máximo de videos a subir |

**Qué hace:**
1. Busca videos `video_*.mp4` en `channels/{channel}/output/`
2. Sube cada video a YouTube como PRIVADO
3. Usa metadata temporal ("Uploading... (metadata pending)")
4. Guarda video IDs en `output/video_ids.csv`

**Output:**
```
📤 Phase 1: Batch Upload (Private) - Momentum Mindset

Found 6 videos to upload

Uploading 1/6: video_001.mp4
✓ Uploaded: xyz123abc

Uploading 2/6: video_002.mp4
✓ Uploaded: abc456def

[...]

Upload Summary:
  ✓ Uploaded: 6
  ✗ Failed: 0

Next step:
  Run: python -m src.main batch-schedule --channel momentum_mindset
  This will set final metadata and schedule publish times.
```

**Importante:**
- YouTube API limit: ~20 uploads/día (cuenta nueva)
- Videos quedan PRIVADOS hasta que corras `batch-schedule`
- Los IDs se guardan en CSV para la Fase 2

### `batch-schedule`

**Fase 2**: Programa videos subidos con metadata final y horarios óptimos.

```bash
# Preview del schedule (dry run)
python -m src.main batch-schedule --channel momentum_mindset --dry-run

# Programar de verdad
python -m src.main batch-schedule --channel momentum_mindset
```

**Opciones:**

| Opción | Alias | Tipo | Default | Descripción |
|--------|-------|------|---------|-------------|
| `--channel` | | string | primero | Canal a usar |
| `--dry-run` | | bool | false | Preview sin actualizar |

**Qué hace:**
1. Lee `video_ids.csv` del canal
2. Carga metadata de archivos `*_metadata.json`
3. Consulta videos ya programados en YouTube
4. Calcula horarios óptimos (llena gaps)
5. Actualiza cada video con:
   - Título final (SEO-optimizado)
   - Descripción final
   - Tags
   - Horario de publicación

**Output (dry-run):**
```
📅 Phase 2: Batch Schedule - Momentum Mindset

Found 6 uploaded videos

Checking existing scheduled videos on YouTube...
Found 3 already scheduled videos

Scheduled Videos (DRY RUN)

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Video          ┃ Video ID   ┃ Publish (Local)    ┃ Publish (UTC)      ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ video_001.mp4  │ xyz123abc  │ 2025-11-15 06:00   │ 2025-11-15 11:00   │
│ video_002.mp4  │ abc456def  │ 2025-11-15 08:00   │ 2025-11-15 13:00   │
│ video_003.mp4  │ def789ghi  │ 2025-11-15 10:00   │ 2025-11-15 15:00   │
│ video_004.mp4  │ ghi012jkl  │ 2025-11-15 12:00   │ 2025-11-15 17:00   │
│ video_005.mp4  │ jkl345mno  │ 2025-11-15 14:00   │ 2025-11-15 19:00   │
│ video_006.mp4  │ mno678pqr  │ 2025-11-15 16:00   │ 2025-11-15 21:00   │
└────────────────┴────────────┴────────────────────┴────────────────────┘

🔍 Dry run mode - no videos will be updated
```

**Output (real):**
```
📅 Phase 2: Batch Schedule - Momentum Mindset

[... mismo inicio ...]

Updating videos with metadata and schedule...

Scheduling video_001.mp4 (xyz123abc)...
✓ Scheduled for 2025-11-15 06:00

Scheduling video_002.mp4 (abc456def)...
✓ Scheduled for 2025-11-15 08:00

[...]

Schedule Summary:
  ✓ Scheduled: 6
  ✗ Failed: 0

Done!
Check YouTube Studio to verify scheduled videos.
```

**Scheduler Inteligente:**
- ✅ Consulta videos ya programados en YouTube
- ✅ Llena gaps en el schedule existente
- ✅ Respeta configuración del canal:
  - `start_hour`: 6 (6 AM)
  - `end_hour`: 16 (4 PM)
  - `interval_hours`: 2 (cada 2 horas)
- ✅ Si hoy está lleno, empieza mañana a las 6 AM
- ✅ Nunca programa dos videos al mismo tiempo

### `schedule-uploads`

**DEPRECATED** - Usa `batch-upload` + `batch-schedule` instead.

Este comando sube y programa en un solo paso (sin la fase 2).

```bash
# Preview
python -m src.main schedule-uploads --dry-run

# Upload y schedule
python -m src.main schedule-uploads

# Con fecha específica
python -m src.main schedule-uploads --start-date 2025-11-20
```

**Por qué no se recomienda:**
- ❌ Si falla a mitad, pierdes progreso
- ❌ No puedes revisar antes de programar
- ✅ Mejor: `batch-upload` (resiliente) + `batch-schedule` (con dry-run)

---

## Opciones Globales

Estas opciones se aplican a **todos** los comandos:

### `--verbose` / `-v`

Activa logging detallado.

```bash
python -m src.main --verbose {comando}
python -m src.main -v {comando}
```

**Qué hace:**
- Cambia log level a DEBUG
- Guarda logs en `output/logs/youtube_shorts_{timestamp}.log`
- Muestra tiempos de cada operación
- Stack traces completos en errores

**Ejemplo:**
```
[LLM script generation] Completed in 5.23s
[Scene 1 - Image generation] Completed in 6.45s
[Scene 1 - TTS generation] Completed in 18.32s
[Scene 1 - Video generation] Completed in 2.11s
[Video merge with music] Completed in 1.05s
[Generate video: Transform Your Life] Completed in 182.45s
```

### `--help`

Muestra ayuda del comando.

```bash
python -m src.main {comando} --help
```

**Ejemplos:**
```bash
python -m src.main --help              # Ayuda general
python -m src.main generate --help     # Ayuda de generate
python -m src.main batch-upload --help # Ayuda de batch-upload
```

---

## Workflows Comunes

### Workflow Diario - Un Canal

```bash
# 1. Generar videos
python -m src.main generate --channel momentum_mindset --count 6 --update

# 2. Revisar en output/
ls -lh channels/momentum_mindset/output/

# 3. Subir a YouTube
python -m src.main batch-upload --channel momentum_mindset

# 4. Preview schedule
python -m src.main batch-schedule --channel momentum_mindset --dry-run

# 5. Confirmar schedule
python -m src.main batch-schedule --channel momentum_mindset

# 6. Verificar en YouTube Studio
```

### Workflow Semanal - Todos los Canales

```bash
# 1. Generar para todos los canales AI
python -m src.main batch-all --count 21 --update  # 7 días × 3 videos/día

# 2. Subir por canal
python -m src.main batch-upload --channel momentum_mindset
python -m src.main batch-upload --channel wealth_wisdom

# 3. Programar por canal
python -m src.main batch-schedule --channel momentum_mindset
python -m src.main batch-schedule --channel wealth_wisdom
```

### Workflow de Testing

```bash
# 1. Validar config
python -m src.main validate-config

# 2. Check server
python -m src.main check-server

# 3. Listar canales
python -m src.main list-channels

# 4. Generar 1 video de prueba con verbose
python -m src.main -v generate --channel momentum_mindset --count 1

# 5. Revisar output
ls -lh channels/momentum_mindset/output/
```

---

## Tips y Mejores Prácticas

### 1. Usa `--dry-run` para Scheduling

```bash
# SIEMPRE preview primero
python -m src.main batch-schedule --channel momentum_mindset --dry-run

# Si se ve bien, ejecuta
python -m src.main batch-schedule --channel momentum_mindset
```

### 2. Genera en Lotes Pequeños

```bash
# ✅ Mejor: Lotes de 6
python -m src.main generate --channel momentum_mindset --count 6

# ❌ Evitar: Lotes muy grandes
python -m src.main generate --channel momentum_mindset --count 50
```

**Por qué:**
- Más fácil de debuggear si algo falla
- Menos tiempo perdido si hay un error
- Puedes ajustar config entre lotes

### 3. Usa Verbose para Debugging

```bash
# Si algo falla, re-run con -v
python -m src.main -v generate --channel momentum_mindset --count 1

# Revisa logs
tail -f output/logs/youtube_shorts_*.log
```

### 4. Actualiza Stories Periódicamente

```bash
# Una vez al día o cuando necesites contenido nuevo
python -m src.main update-stories --subreddit selfimprovement --limit 25
```

### 5. Respeta Límites de API

- **YouTube**: Max ~20 uploads/día (cuenta nueva)
- **Together.ai**: Rate limits en free tier
- **Gemini**: Rate limits en free tier

Si llegas al límite:
```bash
# Usa --limit para controlar
python -m src.main batch-upload --channel momentum_mindset --limit 10
```

---

## Variables de Entorno Útiles

Estas afectan el comportamiento de los comandos:

```bash
# En .env

# Logging
LOG_TO_FILE=true              # Guardar logs
LOG_MAX_AGE_DAYS=7           # Retención de logs
VERBOSE=false                # Verbose por default

# SEO
SEO_ENABLED=true             # Generar metadata SEO

# Media Server
MEDIA_SERVER_URL=http://localhost:8000
MEDIA_PROCESSING_TIMEOUT=600  # Timeout en segundos

# Perfiles
PROFILES_PATH=config/profiles.yaml
ACTIVE_PROFILE=frank_motivational  # Default profile

# YouTube
YOUTUBE_PRIVACY_STATUS=private  # public/private/unlisted
YOUTUBE_CATEGORY_ID=22         # People & Blogs
```

---

## Errores Comunes y Soluciones

### `ModuleNotFoundError: No module named 'click'`

**Solución:**
```bash
# Activa el venv
source .venv/bin/activate

# Reinstala
uv pip install -e .
```

### `ValidationError: Field required [type=missing]`

**Solución:**
```bash
# Crea .env
python -m src.main init

# Edita y agrega API keys
nano .env

# Valida
python -m src.main validate-config
```

### `No channels found`

**Solución:**
```bash
# Verifica que exista channels/
ls channels/

# Verifica channel.yaml files
ls channels/*/channel.yaml
```

### `credentials.json not found`

**Solución:**
```bash
# Coloca credentials.json en cada canal
cp credentials.json channels/momentum_mindset/
cp credentials.json channels/wealth_wisdom/
cp credentials.json channels/finance_wins/
```

---

¿Necesitas ayuda con un comando específico? Usa `--help`:

```bash
python -m src.main {comando} --help
```
