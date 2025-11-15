# Testing Guide - Validación Completa del Sistema

Guía para validar que el sistema multi-canal funciona correctamente después de las correcciones.

## Pre-requisitos

1. **Media server corriendo**: `http://localhost:8000`
2. **Credenciales configuradas**: API keys en `.env`
3. **Canales configurados**: credentials.json en cada canal

---

## Pruebas Paso a Paso

### 0️⃣ Preparación

```bash
# Activar entorno virtual
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar/actualizar dependencias
uv pip install -e .
```

---

### 1️⃣ Validación Automática del Sistema

```bash
# Ejecutar script de validación completo
python scripts/validate_system.py
```

**Debe mostrar:**
- ✓ Media server corriendo
- ✓ Canales configurados (momentum_mindset, wealth_wisdom, finance_wins)
- ✓ Profiles cargados correctamente
- ✓ Configuraciones independientes por canal

**Si falla:**
- Media server: Inicia el servidor local
- Credentials: Coloca `credentials.json` en `channels/<canal>/`
- Profiles: Verifica que exista `channels/<canal>/profiles.yaml`

---

### 2️⃣ Validación de Configuración (Manual)

```bash
# Listar canales disponibles
python -m src.main list-channels

# Validar configuración general
python -m src.main validate-config

# Verificar media server
python -m src.main check-server
```

---

### 3️⃣ Actualización de Historias de Reddit

#### Canal: momentum_mindset

```bash
# Actualizar 1 historia para momentum_mindset
python -m src.main update-stories --channel momentum_mindset --limit 1

# Debe:
# - Scrapear r/selfimprovement
# - Guardar en Google Sheets tab "momentum_mindset"
# - Mostrar: "✓ Saved 1 stories to Google Sheets"
```

**Verificar en Google Sheets:**
- Tab: `momentum_mindset`
- Nueva fila con post de r/selfimprovement

#### Canal: wealth_wisdom

```bash
# Actualizar 1 historia para wealth_wisdom
python -m src.main update-stories --channel wealth_wisdom --limit 1

# Debe:
# - Scrapear r/personalfinance
# - Guardar en Google Sheets tab "wealth_wisdom"
# - Mostrar: "✓ Saved 1 stories to Google Sheets"
```

**Verificar en Google Sheets:**
- Tab: `wealth_wisdom`
- Nueva fila con post de r/personalfinance

---

### 4️⃣ Generación de Videos (1 por canal)

#### Canal: momentum_mindset

```bash
# Generar 1 video para momentum_mindset
python -m src.main generate --channel momentum_mindset --count 1 --verbose

# Debe mostrar en los logs:
# - "Using channel: Momentum Mindset"
# - "Using profile: Frank - Motivational"
# - "Using Google Sheets tab: momentum_mindset"
# - content_type: "motivational speech"
# - art_style: "cinematic, dramatic lighting..." (inspirational)
# - NINGUNA mención a "financial" o "personalfinance"
```

**Output esperado:**
- `channels/momentum_mindset/output/video_001.mp4`
- `channels/momentum_mindset/output/video_001_metadata.json`

**Verificar metadata.json:**
```json
{
  "title": "Motivational title here",
  "description": "...",
  "tags": ["motivation", "self improvement", ...],
  "profile": "frank_motivational"
}
```

#### Canal: wealth_wisdom

```bash
# Generar 1 video para wealth_wisdom
python -m src.main generate --channel wealth_wisdom --count 1 --verbose

# Debe mostrar en los logs:
# - "Using channel: Wealth Wisdom"
# - "Using profile: Frank - Young Professional Trader"
# - "Using Google Sheets tab: wealth_wisdom"
# - "Using CUSTOM script prompt from channel" ✅
# - content_type: "financial advice and money wisdom"
# - art_style: "cinematic high-contrast... gold tones..." (luxury finance)
# - NINGUNA mención a "motivational" o "selfimprovement"
```

**Output esperado:**
- `channels/wealth_wisdom/output/video_001.mp4`
- `channels/wealth_wisdom/output/video_001_metadata.json`

**Verificar metadata.json:**
```json
{
  "title": "Finance title with numbers/success",
  "description": "...",
  "tags": ["finance", "money", "investing", ...],
  "profile": "frank_professional"
}
```

**Verificar el video:**
- ✅ Tone "humble brag" (éxitos financieros personales)
- ✅ Imágenes de lujo (yates, relojes, charts, gold/green tones)
- ✅ Contenido financiero (NO motivacional)

---

### 5️⃣ Batch Generation (3 videos por canal)

```bash
# Generar 3 videos para cada canal AI + actualizar historias
python -m src.main batch-all --count 3 --update --verbose

# Debe:
# 1. Actualizar historias de Reddit para ambos canales
# 2. Generar 3 videos para momentum_mindset
# 3. Generar 3 videos para wealth_wisdom
# 4. Mostrar tabla resumen con resultados
```

**Output esperado:**
```
📺 Batch Processing All Channels

Channel: momentum_mindset
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Updated 3 stories from r/selfimprovement
✓ Generated 3 videos

Channel: wealth_wisdom
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Updated 3 stories from r/personalfinance
✓ Generated 3 videos

Summary
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ Channel         ┃ Videos  ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ momentum_mindset│ 3       │ ✓ Success │
│ wealth_wisdom   │ 3       │ ✓ Success │
└─────────────────┴─────────┴───────────┘
```

**Verificar outputs:**
- `channels/momentum_mindset/output/video_002.mp4` ... `video_004.mp4`
- `channels/wealth_wisdom/output/video_002.mp4` ... `video_004.mp4`

---

### 6️⃣ Batch Upload (2-Phase System)

#### Fase 1: Upload (Subir como privados)

```bash
# Subir videos de momentum_mindset como privados
python -m src.main batch-upload --channel momentum_mindset --verbose

# Debe:
# - Subir todos los videos .mp4 sin video_id
# - Crear como PRIVADOS
# - Guardar video IDs en channels/momentum_mindset/output/video_ids.csv
# - Mostrar: "✓ Uploaded X videos"

# Subir videos de wealth_wisdom como privados
python -m src.main batch-upload --channel wealth_wisdom --verbose

# Debe:
# - Subir todos los videos .mp4 sin video_id
# - Crear como PRIVADOS
# - Guardar video IDs en channels/wealth_wisdom/output/video_ids.csv
# - Mostrar: "✓ Uploaded X videos"
```

**Verificar:**
- `channels/momentum_mindset/output/video_ids.csv` contiene video IDs
- `channels/wealth_wisdom/output/video_ids.csv` contiene video IDs
- YouTube Studio: Videos aparecen como PRIVADOS

**Nota:** Si tienes muchos videos, usa `--limit` para respetar cuota API:
```bash
python -m src.main batch-upload --channel momentum_mindset --limit 10
```

---

#### Fase 2: Schedule (Programar publicación)

```bash
# Preview del schedule (dry-run)
python -m src.main batch-schedule --channel momentum_mindset --dry-run

# Debe mostrar:
# - Videos a programar
# - Fechas/horas calculadas
# - Gaps detectados en calendario existente
# - NO ejecuta cambios

# Ejecutar scheduling para momentum_mindset
python -m src.main batch-schedule --channel momentum_mindset --verbose

# Debe:
# - Leer video IDs del CSV
# - Leer metadata de JSON files
# - Actualizar videos con metadata final
# - Programar fechas/horas de publicación
# - Fill gaps en calendario existente
# - Mostrar: "✓ Scheduled X videos"

# Ejecutar scheduling para wealth_wisdom
python -m src.main batch-schedule --channel wealth_wisdom --verbose
```

**Verificar en YouTube Studio:**
- Videos ya NO son privados (programados)
- Fechas de publicación configuradas
- Metadata correcta (titles, descriptions, tags)
- Schedule respeta configuración de cada canal:
  - momentum_mindset: 6 AM - 4 PM, cada 2 horas
  - wealth_wisdom: 6 AM - 4 PM, cada 2 horas

---

## 7️⃣ Validaciones Post-Generación

### Verificar Independencia de Canales

```bash
# Comparar metadata de ambos canales
cat channels/momentum_mindset/output/video_001_metadata.json | jq '.tags'
cat channels/wealth_wisdom/output/video_001_metadata.json | jq '.tags'

# Deben ser DIFERENTES:
# momentum → ["motivation", "self improvement", "mindset", ...]
# wealth → ["finance", "money", "investing", "crypto", ...]
```

### Verificar Custom Prompts (wealth_wisdom)

```bash
# Ver primeras escenas del script generado para wealth_wisdom
cat channels/wealth_wisdom/output/video_001_metadata.json | jq '.original_description'

# Debe contener:
# - Tone "humble brag" ("I made $X", "My portfolio...")
# - Referencias a éxito financiero personal
# - Lenguaje de trading/inversión
# - NO debe ser motivacional genérico
```

### Verificar Logs Detallados

```bash
# Revisar logs con verbose mode
ls -la output/logs/

# Abrir último log
cat output/logs/youtube_shorts_*.log | grep -E "Using channel|Using profile|content_type|art_style"

# Debe mostrar:
# - Canales correctos
# - Profiles correctos
# - Configuraciones independientes
```

---

## ✅ Checklist de Validación

### Configuración
- [ ] Media server corriendo en localhost:8000
- [ ] Dependencias instaladas (`python scripts/validate_system.py`)
- [ ] Canales configurados con credentials.json
- [ ] Profiles.yaml en cada canal
- [ ] Custom prompts en wealth_wisdom (script.txt, image.txt)

### Actualización de Historias
- [ ] momentum_mindset scrapes r/selfimprovement
- [ ] wealth_wisdom scrapes r/personalfinance
- [ ] Historias guardadas en tabs correctos de Google Sheets

### Generación de Videos
- [ ] momentum_mindset genera contenido motivacional
- [ ] wealth_wisdom genera contenido financiero con "humble brag"
- [ ] Art styles son diferentes (inspirational vs luxury finance)
- [ ] Profiles son diferentes (frank_motivational vs frank_professional)
- [ ] Custom prompts se usan en wealth_wisdom

### Batch Processing
- [ ] batch-all procesa ambos canales correctamente
- [ ] Outputs van a directorios correctos por canal
- [ ] Metadata JSON contiene información correcta

### Upload & Scheduling
- [ ] batch-upload sube como privados
- [ ] video_ids.csv se genera correctamente
- [ ] batch-schedule programa con metadata final
- [ ] Schedule respeta horarios de cada canal
- [ ] Fill gaps funciona correctamente

---

## 🐛 Troubleshooting

### Error: "Media server not accessible"
```bash
# Verificar que el server esté corriendo
curl http://localhost:8000/health

# Si no responde, inicia el media server
cd server
python server.py
```

### Error: "No stories found"
```bash
# Verificar conectividad a Reddit
curl https://www.reddit.com/r/selfimprovement/top.json?t=month&limit=5

# Si falla, verifica tu conexión a internet
```

### Error: "Invalid credentials"
```bash
# Verificar que credentials.json exista
ls -la channels/momentum_mindset/credentials.json

# Verificar que .env tenga API keys
cat .env | grep API_KEY
```

### Error: "Channel uses wrong config"
```bash
# Ejecutar validación de prioridades
python scripts/validate_system.py

# Debe mostrar configuraciones diferentes para cada canal
```

### Videos tienen contenido incorrecto
```bash
# Verificar logs con verbose
python -m src.main generate --channel wealth_wisdom --count 1 --verbose 2>&1 | grep -E "content_type|art_style|custom prompt"

# Debe mostrar:
# - content_type: "financial advice and money wisdom"
# - "Using CUSTOM script prompt from channel"
# - art_style con "gold tones"
```

---

## 📊 Métricas de Éxito

**Sistema funcionando correctamente si:**

1. ✅ Cada canal genera contenido independiente
2. ✅ wealth_wisdom usa custom prompts (humble brag tone)
3. ✅ Art styles son diferentes entre canales
4. ✅ Metadata JSON contiene tags apropiados por canal
5. ✅ Google Sheets actualiza tabs correctos
6. ✅ 2-phase upload/schedule funciona sin errores
7. ✅ Videos programados respetan horarios de cada canal

---

## 🚀 Workflow de Producción Recomendado

```bash
# 1. Generar contenido del mes (ej: 90 videos por canal)
python -m src.main batch-all --count 90 --update

# 2. Subir en lotes respetando cuota API (20/día)
python -m src.main batch-upload --channel momentum_mindset --limit 20
python -m src.main batch-upload --channel wealth_wisdom --limit 20

# 3. Al día siguiente, programar todo
python -m src.main batch-schedule --channel momentum_mindset
python -m src.main batch-schedule --channel wealth_wisdom

# 4. Repetir upload+schedule hasta completar todo el contenido
```

**Ventajas:**
- Generas todo el contenido de una vez
- Subes respetando límites de YouTube API
- Programas cuando ya no hay riesgo de rate limits
- Puedes revisar videos antes de programarlos

---

Para más información, ver:
- `.github/CHANNEL_STRUCTURE.md` - Estructura de canales
- `.github/TWO_PHASE_UPLOAD.md` - Sistema 2-phase
- `.github/MULTI_CHANNEL_SYSTEM.md` - Sistema multi-canal
