# Test Scripts para Upload con Scheduling

Dos scripts de prueba para subir los 2 videos de `output/` con scheduling.

## Videos a Procesar

```
output/video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0.mp4
output/video_c53db9e7-2d81-40f2-b50c-1edeb0926163.mp4
```

## Schedule Configurado

```
Video 1: 12 Noviembre 2025, 6:00 AM (America/Chicago)
Video 2: 12 Noviembre 2025, 8:00 PM (America/Chicago)
```

---

## Opción 1: Script Automático (Todo en uno)

**Archivo:** `test_upload_scheduled.py`

Este script hace todo el flujo automáticamente:
1. ✅ Genera metadata SEO para ambos videos
2. ✅ Sube ambos videos como privados
3. ✅ Los programa para publicación

### Uso:

```bash
python tests/integration/test_upload_scheduled.py
```

### Output Esperado:

```
============================================================
🧪 Test: Upload 2 Videos with Scheduling
============================================================

Videos to upload:
  1. video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0.mp4
  2. video_c53db9e7-2d81-40f2-b50c-1edeb0926163.mp4

Scheduled publish times (America/Chicago):
  Video 1: 2025-11-12 06:00
  Video 2: 2025-11-12 20:00

------------------------------------------------------------
STEP 1: Generate Metadata
------------------------------------------------------------

📝 Generating metadata for: video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0.mp4
✓ Metadata saved to: video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0_metadata.json
  Title: Transform Your Mindset: Daily Motivation
  Tags: motivation, mindset, inspiration...

📝 Generating metadata for: video_c53db9e7-2d81-40f2-b50c-1edeb0926163.mp4
✓ Metadata saved to: video_c53db9e7-2d81-40f2-b50c-1edeb0926163_metadata.json
  Title: Overcome Challenges: Motivational Message
  Tags: motivation, challenges, success...

------------------------------------------------------------
STEP 2: Upload Videos with Scheduling
------------------------------------------------------------

📤 Uploading: video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0.mp4
  Title: Transform Your Mindset: Daily Motivation
  Schedule: 2025-11-12 06:00 CST
  Privacy: private (scheduled)
✓ Uploaded successfully!
  Video ID: abc123xyz
  URL: https://www.youtube.com/watch?v=abc123xyz

📤 Uploading: video_c53db9e7-2d81-40f2-b50c-1edeb0926163.mp4
  Title: Overcome Challenges: Motivational Message
  Schedule: 2025-11-12 20:00 CST
  Privacy: private (scheduled)
✓ Uploaded successfully!
  Video ID: def456uvw
  URL: https://www.youtube.com/watch?v=def456uvw

============================================================
✅ Test Complete!
============================================================

Results:
  Video 1: https://www.youtube.com/watch?v=abc123xyz
    Scheduled: 2025-11-12 06:00 CST

  Video 2: https://www.youtube.com/watch?v=def456uvw
    Scheduled: 2025-11-12 20:00 CST

📌 Verify in YouTube Studio:
   https://studio.youtube.com → Content → Videos
   Check that both videos show 'Scheduled' badge
```

---

## Opción 2: Script Paso a Paso (Manual)

**Archivo:** `test_upload_simple.py`

Este script separa el proceso en 2 pasos para mayor control:

### Paso 1: Generar Metadata

```bash
python tests/integration/test_upload_simple.py generate-metadata
```

**Output:**
```
📝 Generating metadata for videos in output/

Found 2 video(s)

1. video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0.mp4
   ✓ Saved: video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0_metadata.json
   Title: Transform Your Mindset: Daily Motivation

2. video_c53db9e7-2d81-40f2-b50c-1edeb0926163.mp4
   ✓ Saved: video_c53db9e7-2d81-40f2-b50c-1edeb0926163_metadata.json
   Title: Overcome Challenges: Motivational Message

✅ Metadata generation complete!
```

### Paso 2: Upload con Scheduling

```bash
python tests/integration/test_upload_simple.py upload-scheduled
```

**Output:**
```
📤 Uploading videos with scheduling

Schedule (America/Chicago):
  Video 1: 2025-11-12 06:00
  Video 2: 2025-11-12 20:00

1. Uploading: video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0.mp4
   ✓ Uploaded: https://www.youtube.com/watch?v=abc123xyz
   Scheduled: 2025-11-12 06:00 CST

2. Uploading: video_c53db9e7-2d81-40f2-b50c-1edeb0926163.mp4
   ✓ Uploaded: https://www.youtube.com/watch?v=def456uvw
   Scheduled: 2025-11-12 20:00 CST

============================================================
✅ Upload Complete!
============================================================

video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0.mp4
  URL: https://www.youtube.com/watch?v=abc123xyz
  Scheduled: 2025-11-12 06:00 CST

video_c53db9e7-2d81-40f2-b50c-1edeb0926163.mp4
  URL: https://www.youtube.com/watch?v=def456uvw
  Scheduled: 2025-11-12 20:00 CST
```

---

## Verificación en YouTube Studio

Después de ejecutar cualquiera de los scripts:

1. Ve a: https://studio.youtube.com
2. Navega a: **Content → Videos**
3. Verifica que ambos videos:
   - Estado: **Private**
   - Badge: **Scheduled**
   - Publish time:
     - Video 1: Nov 12, 2025 at 6:00 AM
     - Video 2: Nov 12, 2025 at 8:00 PM

---

## Archivos Generados

Después de ejecutar, encontrarás en `output/`:

```
output/
├── video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0.mp4
├── video_96b74c8e-98cf-4adf-be4a-a688dfd1c9e0_metadata.json  ← Nuevo
├── video_c53db9e7-2d81-40f2-b50c-1edeb0926163.mp4
└── video_c53db9e7-2d81-40f2-b50c-1edeb0926163_metadata.json  ← Nuevo
```

### Ejemplo de metadata.json:

```json
{
  "title": "Transform Your Mindset: Daily Motivation",
  "description": "Discover powerful strategies to overcome challenges and achieve success. #motivation #mindset #success",
  "tags": [
    "motivation",
    "mindset",
    "inspiration",
    "self-improvement",
    "success",
    "personal development"
  ],
  "category_id": "22"
}
```

---

## Troubleshooting

### Error: No videos found

```bash
❌ No videos found in output/
```

**Solución:** Asegúrate de tener videos en el directorio output/
```bash
ls output/*.mp4
```

### Error: No metadata file found

```bash
❌ Error: No metadata file found!
Run: python tests/integration/test_upload_simple.py generate-metadata
```

**Solución:** Ejecuta primero el paso de generar metadata.

### Error: OAuth authentication required

YouTube abrirá un navegador para autenticación. Sigue los pasos para autorizar.

### Error: Upload failed - Quota exceeded

YouTube tiene límites diarios. Espera 24 horas o solicita aumento de cuota.

---

## Notas Importantes

1. **Timezone**: Los horarios están configurados en `America/Chicago` (tu timezone en `.env`)

2. **Privacy**: Videos se suben como `private` (requerido para scheduling)

3. **Fecha**: Hardcodeada para 12 Noviembre 2025
   - Para cambiar, edita la línea: `tomorrow = datetime(2025, 11, 12, tzinfo=timezone)`

4. **Metadata SEO**: Generada automáticamente con Gemini
   - Títulos optimizados (50-60 chars)
   - Descripciones con keywords
   - 10-15 tags relevantes

5. **Category**: 22 (People & Blogs) - Configurado en `.env`

6. **Synthetic Media**: NO establecido (false) - Correcto para contenido genérico

---

## Comandos Rápidos

```bash
# Opción A: Todo automático
python tests/integration/test_upload_scheduled.py

# Opción B: Paso a paso
python tests/integration/test_upload_simple.py generate-metadata
python tests/integration/test_upload_simple.py upload-scheduled
```

---

## Próximos Pasos

Después de verificar que funcionan estos tests, puedes:

1. **Generar más videos:**
   ```bash
   python -m src.main generate --count 10
   ```

2. **Batch upload con scheduling automático:**
   ```bash
   python -m src.main schedule-uploads --dry-run  # Preview
   python -m src.main schedule-uploads             # Upload
   ```

3. **Custom scheduling:**
   ```bash
   python -m src.main schedule-uploads --start-date 2025-11-15
   ```
