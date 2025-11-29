# Sistema Multi-Canal - Finance Ecosystem

Sistema para gestionar múltiples canales de YouTube desde una sola aplicación.

## 🎯 Arquitectura

### Canales Configurados

```
channels/
├── momentum_mindset/          # Canal 1: Motivación Shorts
├── wealth_wisdom/             # Canal 2: Finance Shorts
└── finance_wins/              # Canal 3: Finance Compilations
```

### Canal 1: MomentumMindset
- **Tipo**: AI Generated Shorts
- **Formato**: 9:16 (Shorts)
- **Duración**: 15-45 segundos
- **Nicho**: Motivación / Self-improvement
- **Audiencia**: 18-35 años
- **CPM**: $2-5
- **Frecuencia**: 6 videos/día (6 AM - 4 PM, cada 2h)
- **Pipeline**: Reddit → Gemini → FLUX → TTS → FFmpeg
- **Voz**: Frank Motivational (energética)

### Canal 2: WealthWisdom
- **Tipo**: AI Generated Shorts
- **Formato**: 9:16 (Shorts)
- **Duración**: 15-45 segundos
- **Nicho**: Finanzas personales / Inversión
- **Audiencia**: 22-40 años, profesionales
- **CPM**: $8-15 💰 (ALTO)
- **Frecuencia**: 6 videos/día (7 AM - 5 PM, cada 2h)
- **Pipeline**: Reddit → Gemini → FLUX → TTS → FFmpeg
- **Voz**: Brody Professional (confiable, profesional)
- **Subreddits**: r/personalfinance, r/Fire, r/investing

### Canal 3: FinanceWins
- **Tipo**: YouTube Compilation
- **Formato**: 16:9 (Videos)
- **Duración**: 3-10 minutos
- **Nicho**: Compilaciones de finance tips
- **Audiencia**: 22-40 años
- **CPM**: $8-15 💰
- **Frecuencia**: 4 videos/día (10 AM - 10 PM, cada 3h)
- **Pipeline**: YouTube Search → yt-dlp → FFmpeg → Upload
- **Costo**: $0 (sin APIs de LLM/Images)

---

## 📁 Estructura de Archivos

```
channels/
└── <channel_name>/
    ├── channel.yaml           # Configuración del canal
    ├── profiles.yaml          # Perfiles de voz/música (AI channels)
    ├── credentials.json       # OAuth credentials (crear manualmente)
    ├── token_youtube.json     # YouTube token (generado automáticamente)
    ├── prompts/               # Prompts personalizados (opcional)
    │   ├── script.txt         # Prompt para generar scripts
    │   ├── image.txt          # Prompt para generar imágenes
    │   └── seo.txt            # Prompt para SEO
    ├── assets/                # Recursos del canal
    │   ├── background_music/  # Música de fondo
    │   └── overlays/          # Overlays para videos
    └── output/                # Videos generados
        ├── video_001.mp4
        ├── video_001_metadata.json
        └── video_ids.csv
```

---

## 🔧 Configuración

### channel.yaml

Archivo principal de configuración de cada canal. Contiene:

- **Información básica**: name, description, handle
- **channel_type**:
  - `ai_generated_shorts` - Shorts con AI
  - `ai_generated_videos` - Videos con AI
  - `youtube_compilation` - Compilaciones de YouTube
- **content**: Configuración de contenido (subreddit, topics, etc.)
- **video**: Formato de video (aspect ratio, width, height)
- **youtube**: Settings de upload (category, schedule, tags)
- **seo**: Configuración de SEO

**Ejemplo** (momentum_mindset):
```yaml
name: "Momentum Mindset"
handle: "@MomentumMindset"
channel_type: "ai_generated_shorts"

content:
  format: "shorts"
  duration_range: [15, 45]
  subreddit: "selfimprovement"

video:
  aspect_ratio: "9:16"
  width: 768
  height: 1344

youtube:
  category_id: "22"  # People & Blogs
  schedule:
    videos_per_day: 6
    start_hour: 6
    end_hour: 16
    interval_hours: 2
```

---

## 🚀 Uso del Sistema

### 1. Listar Canales Disponibles

```bash
python -m src.main list-channels
```

Output:
```
📺 Available Channels

┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Channel         ┃ Name           ┃ Type          ┃ Handle        ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ momentum_mindset│ Momentum Mind..│ AI Shorts     │ @Momentum...  │
│ wealth_wisdom   │ Wealth Wisdom  │ AI Shorts     │ @WealthWi...  │
│ finance_wins    │ Finance Wins...│ Compilation   │ @FinanceW...  │
└─────────────────┴────────────────┴───────────────┴───────────────┘
```

### 2. Generar Contenido para un Canal

**Nota**: Soporte para `--channel` flag será implementado en la siguiente sesión.

Por ahora, el sistema usa el canal default (momentum_mindset).

**Próximamente**:
```bash
# Generar para canal específico
python -m src.main generate --channel momentum_mindset --count 6
python -m src.main generate --channel wealth_wisdom --count 6
python -m src.main generate --channel finance_wins --count 4
```

---

## 📊 Comparación de Canales

| Feature | MomentumMindset | WealthWisdom | FinanceWins |
|---------|-----------------|--------------|-------------|
| **Formato** | 9:16 Shorts | 9:16 Shorts | 16:9 Videos |
| **Duración** | 15-45s | 15-45s | 3-10 min |
| **Pipeline** | Full AI | Full AI | Compilation |
| **Costo/video** | ~$0.10 | ~$0.10 | $0 |
| **Tiempo/video** | ~3 min | ~3 min | ~5-10 min |
| **CPM** | $2-5 | $8-15 💰 | $8-15 💰 |
| **Videos/día** | 6 | 6 | 4 |
| **Horario** | 6AM-4PM | 7AM-5PM | 10AM-10PM |

**Total diario**:
- 16 videos/día
- ~$1.20 en APIs (solo AI channels)
- ~1.5-2 horas trabajo

---

## 🔑 Setup de OAuth por Canal

Cada canal necesita sus propias credenciales de YouTube:

### Opción A: Diferentes Cuentas de YouTube

Cada canal en una cuenta diferente:

1. Crear cuenta de YouTube para cada canal
2. Descargar credentials.json de cada cuenta
3. Copiar a cada directorio:
   ```bash
   cp ~/Downloads/credentials_momentum.json channels/momentum_mindset/credentials.json
   cp ~/Downloads/credentials_wealth.json channels/wealth_wisdom/credentials.json
   cp ~/Downloads/credentials_finance.json channels/finance_wins/credentials.json
   ```

### ⚠️ Importante: Autenticación y Múltiples Cuentas

Para evitar problemas donde el navegador usa una cuenta equivocada por caché (ej: subir video del Canal A usando la sesión del Canal B), el sistema ahora **fuerza la pantalla de consentimiento** cada vez que necesita autenticar.

**Flujo de Autenticación Esperado:**

Cuando ejecutes un comando (ej: `generate` o `batch-upload`), es posible que veas **dos ventanas de autenticación consecutivas**:

1. **Google Sheets (Cuenta Principal)**:
   - Permiso: `View and manage your Google Sheets spreadsheets`
   - **Acción**: Selecciona la cuenta donde tienes tu hoja de cálculo de control.

2. **YouTube (Cuenta del Canal)**:
   - Permiso: `Manage your YouTube videos`
   - **Acción**: Selecciona la cuenta CORRESPONDIENTE al canal que estás procesando (ej: selecciona la cuenta de `@MomentumMindset` si estás trabajando en ese canal).

**Nota**: Si seleccionas la cuenta equivocada, recibirás un error de "Resource not authorized". Si esto pasa, borra el archivo `token_youtube.json` del canal y vuelve a intentar.

### Opción B: Misma Cuenta (Simplificado)

Todos los canales en la misma cuenta de YouTube:

```bash
# Copiar mismo credentials.json a todos
cp ~/Downloads/credentials.json channels/momentum_mindset/credentials.json
cp ~/Downloads/credentials.json channels/wealth_wisdom/credentials.json
cp ~/Downloads/credentials.json channels/finance_wins/credentials.json
```

**Nota**: Con esta opción, todos los videos van al mismo canal de YouTube, pero puedes organizarlos con playlists.

---

## 🎨 Diferenciación Visual

### MomentumMindset
- **Estilo visual**: Cinematic, dramatic lighting, golden hour
- **Colores**: Warm tones, naranja, dorado
- **Música**: Épica, upbeat, inspiracional
- **Voz**: Energética, motivacional

### WealthWisdom
- **Estilo visual**: Modern, professional, sleek
- **Colores**: Verde (money), azul (trust), negro/oro
- **Música**: Corporate smooth, jazz profesional
- **Voz**: Confiable, autoritaria, profesional

### FinanceWins
- **Estilo visual**: Compilación con text overlays
- **Colores**: Verde, negro, oro
- **Música**: Corporate upbeat
- **Voz**: N/A (compilación)

---

## 📝 Próximos Pasos (TODO)

### Fase 1 ✅ (Completada)
- [x] Crear estructura `channels/`
- [x] Implementar `ChannelConfig` class
- [x] Configurar 3 canales (momentum, wealth, finance)
- [x] Crear comando `list-channels`

### Fase 2 (Siguiente Sesión)
- [ ] Agregar `--channel` flag a comandos CLI
  - [ ] `generate --channel <name>`
  - [ ] `batch-upload --channel <name>`
  - [ ] `batch-schedule --channel <name>`
- [ ] Modificar `WorkflowOrchestrator` para usar `ChannelConfig`
- [ ] Modificar services para cargar configs por canal:
  - [ ] LLM service (prompts personalizados)
  - [ ] YouTube service (OAuth por canal)
  - [ ] ProfileManager (perfiles por canal)

### Fase 3 (Futuro)
- [ ] Implementar `VideoCompiler` para finance_wins
- [ ] Implementar `YouTubeDownloader` service
- [ ] Comando `batch-all` para procesar todos los canales
- [ ] Dashboard de estado de canales

---

## 🐛 Troubleshooting

### Error: "Channel directory not found"

```bash
# Listar canales disponibles
python -m src.main list-channels

# Verificar que exista el directorio
ls channels/
```

### Error: "Config file not found"

Cada canal necesita un archivo `channel.yaml`:
```bash
ls channels/momentum_mindset/channel.yaml
```

### Error: "credentials.json not found"

Cada canal necesita sus credenciales de YouTube:
```bash
# Copiar credentials.json a cada canal
cp ~/Downloads/credentials.json channels/<channel_name>/credentials.json
```

---

## 📚 Recursos

### Subreddits Recomendados

**Finance/Money**:
- r/personalfinance (3.8M members)
- r/Fire (1.2M members) - Financial Independence
- r/financialindependence (1.6M members)
- r/investing (2.4M members)
- r/stocks (5.8M members)
- r/Money (800K members)

**Motivación**:
- r/selfimprovement (1.4M members)
- r/getdisciplined (1.3M members)
- r/DecidingToBeBetter (350K members)
- r/productivity (430K members)

**Nota**: Los subreddits ya están configurados en cada `channel.yaml` pero puedes modificarlos según necesites.

---

## 🎯 Finance Ecosystem Strategy

### Por qué este trio funciona:

1. **Audiencia compartida**
   - Canal 2 y 3 = mismo nicho (finanzas)
   - Se promocionan mutuamente

2. **Formatos complementarios**
   - Shorts (viral) + Videos largos (profundidad)
   - Diferentes preferencias de consumo

3. **CPM alto**
   - 2/3 canales con CPM alto ($8-15)
   - Mejor monetización

4. **Diversificación de contenido**
   - Original (AI) + Compilación
   - Menos riesgo

5. **Bajo mantenimiento**
   - Todo automatizado
   - Misma aplicación gestiona los 3

---

## 💡 Tips

1. **Empieza con MomentumMindset**
   - Ya está funcionando
   - Valida el sistema

2. **Luego WealthWisdom**
   - Mismo pipeline que Momentum
   - Solo cambian prompts/voz

3. **FinanceWins al final**
   - Requiere implementación adicional
   - (YouTubeDownloader + VideoCompiler)

4. **Testea cada canal**
   - 1 video por canal para validar
   - Verifica OAuth, schedule, metadata

5. **Monitorea CPM**
   - Finance debería tener CPM 2-3x más alto
   - Ajusta estrategia según resultados

---

**Version**: v0.4.0 (Multi-Channel System)
**Last Updated**: 2025-11-13
**Status**: Phase 1 Complete ✅
