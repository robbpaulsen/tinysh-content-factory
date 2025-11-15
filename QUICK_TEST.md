# Quick Test - Comandos de Validación Rápida

Ejecuta estos comandos en tu máquina local (Windows) con el media server corriendo.

## ✅ Pre-requisitos

```bash
# 1. Activar entorno
.venv\Scripts\activate

# 2. Verificar que tienes .env configurado con tus API keys
cat .env | findstr API_KEY

# 3. Media server debe estar corriendo
# En otra terminal: cd server && python server.py
```

---

## 🧪 Pruebas Rápidas (5 minutos)

```bash
# 1. Validación automática
python scripts/validate_system.py

# 2. Actualizar 1 historia momentum_mindset
python -m src.main update-stories --channel momentum_mindset --limit 1

# 3. Actualizar 1 historia wealth_wisdom
python -m src.main update-stories --channel wealth_wisdom --limit 1

# 4. Generar 1 video momentum_mindset
python -m src.main generate --channel momentum_mindset --count 1 --verbose

# 5. Generar 1 video wealth_wisdom (con custom prompts)
python -m src.main generate --channel wealth_wisdom --count 1 --verbose
```

**Busca en los logs de wealth_wisdom:**
- ✅ "Using CUSTOM script prompt from channel"
- ✅ content_type: "financial advice and money wisdom"
- ✅ Profile: "Frank - Young Professional Trader"

---

## 🎯 Prueba Completa (30-60 minutos)

```bash
# 1. Batch generation (3 videos por canal = 6 videos total)
python -m src.main batch-all --count 3 --update --verbose

# 2. Upload todos (momentum)
python -m src.main batch-upload --channel momentum_mindset

# 3. Upload todos (wealth)
python -m src.main batch-upload --channel wealth_wisdom

# 4. Schedule todos (momentum) - DRY RUN primero
python -m src.main batch-schedule --channel momentum_mindset --dry-run

# 5. Schedule todos (momentum) - REAL
python -m src.main batch-schedule --channel momentum_mindset

# 6. Schedule todos (wealth) - DRY RUN primero
python -m src.main batch-schedule --channel wealth_wisdom --dry-run

# 7. Schedule todos (wealth) - REAL
python -m src.main batch-schedule --channel wealth_wisdom
```

---

## ✅ Verificación Post-Pruebas

```bash
# Verificar outputs
dir channels\momentum_mindset\output
dir channels\wealth_wisdom\output

# Comparar metadata
type channels\momentum_mindset\output\video_001_metadata.json
type channels\wealth_wisdom\output\video_001_metadata.json

# Ver tags (deben ser diferentes)
# momentum → motivation, self improvement, mindset
# wealth → finance, money, investing, crypto
```

---

## 🚨 Si algo falla

1. **Media server no responde:**
   ```bash
   curl http://localhost:8000/health
   # Si falla, reinicia: cd server && python server.py
   ```

2. **Custom prompts no se usan (wealth_wisdom):**
   ```bash
   # Verificar que existan
   dir channels\wealth_wisdom\prompts
   # Debe tener: script.txt, image.txt
   ```

3. **Canales usan misma config:**
   ```bash
   python scripts/validate_system.py
   # Debe mostrar configs diferentes
   ```

4. **Rate limit de YouTube:**
   ```bash
   # Usa --limit para respetar cuota
   python -m src.main batch-upload --channel momentum_mindset --limit 10
   ```

---

## 📊 Checklist de Éxito

Marca cada item después de ejecutar:

**Configuración:**
- [ ] `python scripts/validate_system.py` → todo ✓
- [ ] Media server responde en localhost:8000

**Actualización:**
- [ ] momentum scrapes r/selfimprovement
- [ ] wealth scrapes r/personalfinance

**Generación:**
- [ ] momentum usa art style inspiracional
- [ ] wealth usa art style luxury finance
- [ ] wealth usa custom prompts ("humble brag")
- [ ] Metadata JSONs son diferentes

**Upload/Schedule:**
- [ ] Videos suben como privados
- [ ] video_ids.csv se genera
- [ ] Schedule actualiza metadata
- [ ] Videos programados en YouTube Studio

---

Ver guía completa en: `.github/TESTING_GUIDE.md`
