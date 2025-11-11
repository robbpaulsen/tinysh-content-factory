# Chatterbox TTS - Instalación que Funciona

**Fecha**: 2025-11-06
**Probado en**: Windows con uv

Este método de instalación **funciona sin problemas** con chatterbox-tts. El orden de los pasos es crítico.

---

## ⚠️ NOTA IMPORTANTE

**SE TIENEN QUE EJECUTAR LOS PASOS EN EL ORDEN INDICADO**

No se garantiza la funcionalidad si no se hace en ese mismo orden.

---

## 📋 Pasos de Instalación

### 1. Inicializar proyecto nuevo con uv

```bash
# Crear directorio nuevo e inicializar con Python 3.11
uv init --python cp311 --pin-python --no-readme --no-workspace
```

**Flags importantes**:
- `--python cp311` - Usar Python 3.11 específicamente
- `--pin-python` - Fijar la versión de Python
- `--no-readme` - No crear README.md
- `--no-workspace` - No crear workspace

---

### 2. Generar entorno virtual

```bash
# Generar entorno con versión Python cp311 pinneada
uv venv
```

---

### 3. Activar entorno virtual

**Windows (PowerShell)**:
```powershell
. .\.venv\Scripts\activate.ps1
```

**Linux/Mac**:
```bash
source .venv/bin/activate
```

---

### 4. Instalar Chatterbox desde Git (PRIMERO)

```bash
# Instalar chatterbox-tts desde repositorio Git (versión específica)
uv add "chatterbox-tts @ git+https://github.com/resemble-ai/chatterbox.git@v0.1.2"
```

**Por qué primero**: Chatterbox define sus propias dependencias de torch, instalar esto primero evita conflictos.

---

### 5. Instalar PyTorch con rangos amplios

```bash
# Agregar torch con rango amplio de versionado
uv add "torch>=2.0.0,<2.7.0"

# Agregar torchaudio con rango amplio
uv add "torchaudio>=2.0.0,<2.7.0"
```

**Por qué rangos amplios**: Permite que uv resuelva la mejor versión compatible con chatterbox sin conflictos.

---

### 6. Agregar dependencias mínimas necesarias

```bash
# FastAPI (necesario para chatterbox server)
uv add "fastapi>=0.104.0"

# Uvicorn con extras estándar
uv add "uvicorn[standard]>=0.24.0"

# Pydantic (validación)
uv add "pydantic>=2.0.0"

# Python-dotenv (variables de entorno)
uv add "python-dotenv>=1.0.0"

# Requests (opcional, para testing)
uv add "requests>=2.28.0" --optional dev
```

---

### 7. Sincronizar entorno

```bash
# Sincronizar todas las dependencias
uv sync
```

---

## ✅ Verificación de Instalación

### Opción 1: Verificar servidor Chatterbox (si está corriendo)

```bash
# Comprobación de estado del servidor
uv run python -c "
import requests
r = requests.get('http://localhost:4123/health')
print(f'Estado: {r.status_code}')
print(r.json())
"
```

**Salida esperada**:
```
Estado: 200
{'status': 'ok'}
```

---

### Opción 2: Verificar documentación FastAPI

```bash
# Prueba de la documentación de FastAPI
uv run python -c "
import requests
r = requests.get('http://localhost:4123/docs')
print(f'Documentación disponible: {r.status_code == 200}')
"
```

**Salida esperada**:
```
Documentación disponible: True
```

---

### Opción 3: Prueba de generación TTS

```bash
# Prueba de la generación de TTS (requiere tests/test_api.py)
uv run python tests/test_api.py
```

---

## 🔧 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'torch'"

**Solución**: Asegúrate de haber seguido el orden exacto. Reinstala:
1. Elimina `.venv` y `uv.lock`
2. Sigue los pasos desde el inicio

---

### Error: "pkuseg build failed"

**Solución**: Este error suele ocurrir en Windows. El método de instalación arriba evita este error al:
1. Instalar chatterbox primero desde git
2. Usar rangos amplios de versión en torch
3. Dejar que uv resuelva las dependencias automáticamente

---

### Error: Conflictos de versión de torch

**Solución**: Los rangos amplios (`>=2.0.0,<2.7.0`) permiten flexibilidad. Si aún hay conflictos:
1. Revisa `pyproject.toml` para versiones pinneadas innecesarias
2. Usa `uv tree` para ver el árbol de dependencias
3. Considera usar `--resolution lowest` o `--resolution highest` en `uv sync`

---

## 📦 Estructura Final

Después de la instalación, tu `pyproject.toml` debería verse así:

```toml
[project]
name = "your-project"
version = "0.1.0"
description = ""
requires-python = "==3.11.*"
dependencies = [
    "chatterbox-tts @ git+https://github.com/resemble-ai/chatterbox.git@v0.1.2",
    "fastapi>=0.104.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "torch>=2.0.0,<2.7.0",
    "torchaudio>=2.0.0,<2.7.0",
    "uvicorn[standard]>=0.24.0",
]

[project.optional-dependencies]
dev = [
    "requests>=2.28.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
python = "3.11"
```

---

## 🎯 Diferencias Clave vs Instalación Estándar

| Aspecto | Instalación Estándar | Este Método (Funciona) |
|---------|---------------------|------------------------|
| Python | Cualquier versión | **cp311 específicamente** |
| Chatterbox | `uv add chatterbox-tts` | `uv add "chatterbox-tts @ git+..."` |
| PyTorch | Versión exacta | **Rangos amplios** `>=2.0.0,<2.7.0` |
| Orden | No importa | **CRÍTICO** - Chatterbox primero |
| Conflictos | pkuseg build errors | **Sin conflictos** |

---

## 🚀 Uso en Proyectos Existentes

Si quieres integrar esto en un proyecto existente (como `tinysh-content-factory`):

### Opción A: Proyecto separado (recomendado)

1. Crea un directorio separado para chatterbox
2. Sigue los pasos arriba
3. Comunica con el proyecto principal vía API/HTTP

### Opción B: Integración directa (avanzado)

1. Modifica `pyproject.toml` del proyecto existente
2. Agrega chatterbox con `uv add "chatterbox-tts @ git+..."`
3. Ajusta rangos de torch si hay conflictos
4. `uv sync --reinstall` para resolver

---

## 📝 Notas Adicionales

### Por qué funciona este método:

1. **Python 3.11 pinneado**: Chatterbox funciona mejor con Python 3.11
2. **Git install**: Evita problemas de distribución de PyPI con pkuseg
3. **Rangos amplios de torch**: Permite que uv resuelva la mejor versión
4. **Orden de instalación**: Chatterbox primero define las restricciones base

### Limitaciones conocidas:

- Requiere Python 3.11 (no funciona con 3.12+)
- Windows puede requerir Visual Studio Build Tools para algunos paquetes
- Primera instalación puede tardar ~5-10 minutos (PyTorch es grande)

---

## 🔗 Referencias

- **Chatterbox GitHub**: https://github.com/resemble-ai/chatterbox
- **uv Documentation**: https://docs.astral.sh/uv/
- **PyTorch**: https://pytorch.org/

---

**Probado y funcionando**: 2025-11-06
**Plataforma**: Windows con uv
**Python**: 3.11
**Resultado**: ✅ Sin errores, instalación completa exitosa
