# YouTube Shorts Factory - Setup Guide

Guía completa paso a paso para configurar el sistema multi-canal desde cero.

## Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Instalación Básica](#instalación-básica)
- [Configuración del Media Server](#configuración-del-media-server)
- [Setup de Canales](#setup-de-canales)
- [Configuración de OAuth](#configuración-de-oauth)
- [Prueba del Sistema](#prueba-del-sistema)
- [Primeros Videos](#primeros-videos)

---

## Requisitos Previos

### Software Necesario

1. **Python 3.11+**
   ```bash
   python --version
   # Debe mostrar 3.11 o superior
   ```

2. **uv** (package manager)
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **Git**
   ```bash
   git --version
   ```

4. **FFmpeg** (en el media server)
   ```bash
   ffmpeg -version
   ```

5. **yt-dlp** (para canales de compilación)
   ```bash
   pip install yt-dlp
   # o
   brew install yt-dlp  # macOS
   ```

### API Keys Necesarios

Antes de empezar, consigue estos API keys:

1. **Google Gemini API**
   - Ve a: https://makersuite.google.com/app/apikey
   - Crea un API key
   - Copia y guarda el key

2. **Together.ai API**
   - Ve a: https://together.ai/
   - Regístrate
   - Ve a Settings → API Keys
   - Crea un API key
   - Copia y guarda el key

3. **Google Cloud OAuth Credentials**
   - Ve a: https://console.cloud.google.com/
   - Crea un proyecto (o usa uno existente)
   - Habilita estas APIs:
     - Google Sheets API
     - YouTube Data API v3
   - Crea credenciales OAuth 2.0 (Tipo: Desktop app)
   - Descarga el JSON como `credentials.json`
   - Guarda en un lugar seguro

---

## Instalación Básica

### Paso 1: Clonar el Repositorio

```bash
git clone <your-repo-url>
cd tinysh-content-factory
```

### Paso 2: Crear Entorno Virtual

```bash
# Crear venv con uv
uv venv

# Activar venv
source .venv/bin/activate  # macOS/Linux
# o
.venv\Scripts\activate     # Windows
```

### Paso 3: Instalar Dependencias

```bash
# Instalar con uv
uv pip install -e .

# Verificar instalación
python -m src.main --help
```

Deberías ver la ayuda del CLI si todo está correcto.

### Paso 4: Configurar .env

```bash
# Crear .env desde template
python -m src.main init

# Editar .env
nano .env  # o usa tu editor preferido
```

**Configuración mínima en .env:**

```bash
# APIs
GOOGLE_API_KEY="tu_gemini_api_key_aqui"
TOGETHER_API_KEY="tu_together_api_key_aqui"

# Google Sheets
GOOGLE_SHEET_ID="id_de_tu_google_sheet"

# Media Server
MEDIA_SERVER_URL="http://localhost:8000"

# Reddit
SUBREDDIT="selfimprovement"

# SEO (opcional, desactivar para pruebas)
SEO_ENABLED=false

# Logging
LOG_TO_FILE=true
LOG_MAX_AGE_DAYS=7
```

### Paso 5: Validar Configuración

```bash
python -m src.main validate-config
```

Debe mostrar: `✓ Configuration is valid!`

---

## Configuración del Media Server

El media server es **crítico** para el funcionamiento del sistema. Maneja:
- Generación de TTS (Kokoro/Chatterbox)
- Procesamiento de video con FFmpeg
- Generación de captions
- Almacenamiento temporal de archivos

### Verificar Server

```bash
python -m src.main check-server
```

**Si falla:**

1. Verifica que el server esté corriendo en `http://localhost:8000`
2. Revisa logs del media server
3. Asegúrate de que FFmpeg esté instalado
4. Verifica que el puerto 8000 no esté en uso

**Configuración del server** (en el server mismo):

```bash
# Variables de entorno del media server
FFMPEG_ENCODER=auto      # auto/nvenc/x264
FFMPEG_PRESET=p4         # p1-p7 (nvenc) / ultrafast-slow (x264)
FFMPEG_CQ=23             # Calidad (18=best, 28=worst)
FFMPEG_BITRATE=5M
FFMPEG_AUDIO_BITRATE=128k
```

---

## Setup de Canales

Los canales ya están creados en `channels/`, pero necesitas configurarlos según tus necesidades.

### Canales Incluidos

1. **momentum_mindset** - Shorts motivacionales (9:16)
2. **wealth_wisdom** - Shorts de finanzas (9:16)
3. **finance_wins** - Compilaciones de finanzas (16:9)

### Estructura de Cada Canal

```
channels/momentum_mindset/
├── channel.yaml           # ✅ Ya existe - puedes modificar
├── profiles.yaml          # ✅ Ya existe - puedes modificar
├── credentials.json       # ❌ NECESITAS CREAR
├── token_youtube.json     # ✅ Se crea automáticamente
├── assets/                # Para archivos del canal
│   └── .gitkeep
├── output/                # Videos generados
│   └── .gitkeep
└── prompts/               # Para prompts personalizados
    └── README.md
```

### Personalizar channel.yaml

Cada canal tiene su configuración en `channels/{channel_name}/channel.yaml`:

```yaml
name: "Momentum Mindset"
description: "Daily motivation and self-improvement"
handle: "@MomentumMindset"  # ← CAMBIA ESTO
channel_type: "ai_generated_shorts"

content:
  format: "shorts"
  duration_range: [15, 45]  # segundos
  subreddit: "selfimprovement"  # ← Cambia según tu nicho
  topics:
    - self improvement
    - motivation
    - productivity

video:
  aspect_ratio: "9:16"  # 9:16 para shorts, 16:9 para videos
  width: 768
  height: 1344

youtube:
  category_id: "22"  # ← Ver categorías YouTube
  schedule:
    videos_per_day: 6  # Cuántos videos por día
    start_hour: 6      # Hora de inicio (6 AM)
    end_hour: 16       # Hora de fin (4 PM)
    interval_hours: 2  # Cada 2 horas

seo:
  target_keywords:
    - motivation
    - self improvement  # ← Cambia según tu nicho
  default_tags:
    - shorts
    - motivation

default_profile: "frank_motivational"  # ← Perfil de voz/música
```

**Categorías YouTube más comunes:**
- `22` - People & Blogs
- `26` - Howto & Style
- `10` - Music
- `24` - Entertainment
- `28` - Science & Technology

### Personalizar profiles.yaml

Define perfiles de voz y música:

```yaml
profiles:
  frank_motivational:
    name: "Frank - Motivational"
    description: "Energetic, inspiring tone"
    voice:
      engine: chatterbox  # o kokoro
      sample_path: "ruta/a/tu/sample.mp3"  # ← CAMBIA ESTO
      temperature: 0.7
      cfg_weight: 0.65
      exaggeration: 0.55
    music:
      playlist:
        - path: "ruta/a/tu/musica.mp3"  # ← CAMBIA ESTO
          name: "Track Name"
      volume: 0.1  # 0.0 - 1.0
      rotation: random  # random o sequential

default_profile: frank_motivational
```

**Notas importantes:**
- `sample_path`: Audio de ejemplo de la voz (para Chatterbox)
- `playlist`: Puedes agregar múltiples tracks
- `rotation: random` - Selecciona música al azar
- `rotation: sequential` - Rota música en orden

---

## Configuración de OAuth

**IMPORTANTE:** Cada canal necesita credenciales OAuth de YouTube.

### Opción A: Canales en Cuentas Diferentes (Recomendado)

Usa esta opción si quieres separación total entre canales.

**Por cada canal:**

1. **Crear/Usar cuenta de Google**
   - Canal 1: cuenta1@gmail.com → @MomentumMindset
   - Canal 2: cuenta2@gmail.com → @WealthWisdom
   - Canal 3: cuenta3@gmail.com → @FinanceWins

2. **Crear credenciales OAuth para cada cuenta**
   - Ve a https://console.cloud.google.com/
   - Selecciona tu proyecto
   - Credentials → Create Credentials → OAuth 2.0 Client ID
   - Application type: **Desktop app**
   - Name: `momentum_mindset_oauth` (o el nombre de tu canal)
   - Download JSON

3. **Guardar credentials.json en cada canal**
   ```bash
   # Renombra el JSON descargado y cópialo
   cp ~/Downloads/client_secret_xxx.json channels/momentum_mindset/credentials.json
   cp ~/Downloads/client_secret_yyy.json channels/wealth_wisdom/credentials.json
   cp ~/Downloads/client_secret_zzz.json channels/finance_wins/credentials.json
   ```

4. **Autenticar cada canal** (la primera vez que lo uses)
   ```bash
   # Genera videos para momentum_mindset
   python -m src.main generate --channel momentum_mindset --count 1

   # Se abrirá el navegador para autenticar
   # Acepta los permisos
   # El token se guarda automáticamente en channels/momentum_mindset/token_youtube.json
   ```

### Opción B: Todos los Canales en Una Cuenta

Usa esta opción si quieres simplicidad (todos los canales en una cuenta Google).

1. **Usar la misma credentials.json para todos**
   ```bash
   # Copiar el mismo archivo a todos los canales
   cp credencials.json channels/momentum_mindset/credentials.json
   cp credentials.json channels/wealth_wisdom/credentials.json
   cp credentials.json channels/finance_wins/credentials.json
   ```

2. **Autenticar una vez**
   ```bash
   python -m src.main generate --channel momentum_mindset --count 1
   ```

3. **Los tokens se crean automáticamente** para cada canal

**Nota:** Con esta opción, todos los canales comparten la misma cuenta YouTube. Puedes usar Brand Channels para separarlos visualmente.

### Verificar OAuth

```bash
# Listar canales configurados
python -m src.main list-channels

# Deberías ver todos los canales con su configuración
```

---

## Prueba del Sistema

### Paso 1: Verificar Configuración Completa

```bash
# Validar .env
python -m src.main validate-config

# Verificar media server
python -m src.main check-server

# Listar canales
python -m src.main list-channels
```

### Paso 2: Prueba de Google Sheets

```bash
# Actualizar stories desde Reddit
python -m src.main update-stories --subreddit selfimprovement --limit 10
```

Verifica que las stories aparezcan en tu Google Sheet.

### Paso 3: Generar Video de Prueba

```bash
# Generar 1 video para momentum_mindset
python -m src.main generate --channel momentum_mindset --count 1

# Con verbose para ver detalles
python -m src.main -v generate --channel momentum_mindset --count 1
```

**Qué esperar:**
1. Se abre el navegador para OAuth (primera vez)
2. El sistema genera el video paso a paso:
   - ✅ Fetching story from Sheets
   - ✅ Creating script with Gemini
   - ✅ Generating images (FLUX)
   - ✅ Generating TTS
   - ✅ Creating videos with captions
   - ✅ Merging videos
   - ✅ Adding music
   - ✅ Downloading final video

3. Video final en: `channels/momentum_mindset/output/video_001.mp4`

### Paso 4: Verificar el Video

```bash
# Navega al output
cd channels/momentum_mindset/output/

# Deberías ver:
# - video_001.mp4
# - video_001_metadata.json (si SEO está habilitado)
```

Abre el video y verifica:
- ✅ Tiene audio (voz + música)
- ✅ Tiene captions
- ✅ Calidad es buena
- ✅ Aspect ratio correcto (9:16 para shorts)

---

## Primeros Videos

Una vez que todo funciona, puedes generar videos en lote.

### Workflow Completo para Un Canal

```bash
# 1. Generar 6 videos
python -m src.main generate --channel momentum_mindset --count 6 --update

# 2. Revisar videos en output/
ls -lh channels/momentum_mindset/output/

# 3. Subir a YouTube como privados (Fase 1)
python -m src.main batch-upload --channel momentum_mindset

# 4. Programar con metadata y horarios (Fase 2)
python -m src.main batch-schedule --channel momentum_mindset --dry-run  # Preview
python -m src.main batch-schedule --channel momentum_mindset            # Real

# 5. Verificar en YouTube Studio
# Los videos deben estar programados con horarios óptimos
```

### Workflow para Todos los Canales

```bash
# Generar 3 videos para cada canal AI
python -m src.main batch-all --count 3 --update

# Subir todos (hazlo manualmente por canal para control)
python -m src.main batch-upload --channel momentum_mindset
python -m src.main batch-upload --channel wealth_wisdom

# Programar todos
python -m src.main batch-schedule --channel momentum_mindset
python -m src.main batch-schedule --channel wealth_wisdom
```

### Tips para Producción

1. **Empieza con 1-2 videos de prueba**
   - Valida calidad
   - Ajusta configuración si es necesario
   - Prueba diferentes perfiles de voz

2. **Usa dry-run para scheduling**
   ```bash
   python -m src.main batch-schedule --channel momentum_mindset --dry-run
   ```
   - Ve los horarios antes de confirmar
   - Verifica que no haya conflictos

3. **Monitorea logs**
   ```bash
   # Con verbose mode
   python -m src.main -v generate --channel momentum_mindset --count 1

   # Revisa logs
   tail -f output/logs/youtube_shorts_*.log
   ```

4. **Respeta límites de API**
   - YouTube: Max 20 uploads/día (cuenta nueva)
   - Together.ai: Límites en free tier
   - Gemini: Límites en free tier

5. **Optimiza horarios de generación**
   - Genera videos de noche cuando la API no está saturada
   - Programa uploads para la mañana siguiente

---

## Troubleshooting Común

### Error: "No channels found"

```bash
# Verifica que exista la carpeta channels/
ls channels/

# Verifica que haya archivos channel.yaml
ls channels/*/channel.yaml
```

### Error: "credentials.json not found"

```bash
# Verifica que credentials.json exista en cada canal
ls channels/momentum_mindset/credentials.json
ls channels/wealth_wisdom/credentials.json
```

### Error: "Media server not responding"

```bash
# Verifica que el server esté corriendo
curl http://localhost:8000/health

# Si no responde, inicia el media server
# (depende de tu setup de media server)
```

### Error: OAuth "redirect_uri_mismatch"

1. Ve a Google Cloud Console
2. Credentials → Tu OAuth client
3. Verifica que `http://localhost` esté en "Authorized redirect URIs"
4. Agrega si falta
5. Espera unos minutos y reintenta

### Videos sin Audio

1. Verifica que el perfil de voz tenga `sample_path` correcto
2. Verifica que la música exista en la ruta especificada
3. Revisa logs del media server

### Videos con Calidad Baja

Ajusta en el media server:
```bash
FFMPEG_CQ=18    # Mejor calidad (18-28, menor = mejor)
FFMPEG_BITRATE=8M  # Mayor bitrate
```

---

## Próximos Pasos

Una vez que el setup básico funciona:

1. **Personaliza prompts** - Crea prompts personalizados en `channels/{channel}/prompts/`
2. **Optimiza SEO** - Habilita `SEO_ENABLED=true` para metadata automática
3. **Experimenta con perfiles** - Crea diferentes perfiles de voz/música
4. **Automatiza con cron** - Programa generación automática diaria
5. **Monitorea analytics** - Revisa qué tipo de contenido funciona mejor

---

## Recursos Adicionales

- **Documentación Multi-Canal**: `.github/MULTI_CHANNEL_SYSTEM.md`
- **Referencia CLI**: `CLI_REFERENCE.md` (próximamente)
- **Troubleshooting**: `TROUBLESHOOTING.md` (próximamente)
- **README Principal**: `README.md`

---

¿Tienes preguntas? Revisa los logs en `output/logs/` y busca errores específicos.
