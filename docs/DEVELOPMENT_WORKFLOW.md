# Development Workflow

Esta guía documenta el flujo de trabajo de desarrollo para el proyecto TinyShorts Content Factory.

---

## 🌿 Git Branch Strategy

### Regla Principal

**SIEMPRE crear un branch específico para cada feature o bug fix.**

Nunca trabajar directamente en `main` para nuevas funcionalidades o correcciones.

---

## 📋 Workflow Estándar

### 1. Antes de Empezar un Feature/Bug

```bash
# Asegurarse de estar en main y actualizado
git checkout main
git pull origin main

# Crear branch específico
git checkout -b <tipo>/<nombre-descriptivo>
```

### 2. Convenciones de Nombres de Branch

**Formato:** `<tipo>/<descripción-corta>`

**Tipos de Branch:**

| Tipo | Uso | Ejemplo |
|------|-----|---------|
| `feat/` | Nuevas funcionalidades | `feat/quality-presets` |
| `fix/` | Corrección de bugs | `fix/cache-memory-leak` |
| `refactor/` | Refactorización de código | `refactor/media-service` |
| `docs/` | Documentación | `docs/api-reference` |
| `test/` | Tests | `test/cache-integration` |
| `chore/` | Mantenimiento | `chore/update-dependencies` |

**Ejemplos:**
```bash
# Feature
git checkout -b feat/smart-cache
git checkout -b feat/quality-presets
git checkout -b feat/cost-tracker

# Bug fix
git checkout -b fix/tts-timeout
git checkout -b fix/video-merge-paths

# Refactor
git checkout -b refactor/storage-manager
```

---

## 🔄 Ciclo de Desarrollo

### Paso 1: Crear Branch
```bash
git checkout -b feat/nueva-funcionalidad
```

### Paso 2: Desarrollar
- Hacer commits frecuentes
- Seguir convenciones de commit (ver abajo)
- Mantener branch actualizado con main

### Paso 3: Testing
```bash
# Ejecutar tests relevantes
python tests/test_*.py

# Ejecutar todos los tests
pytest
```

### Paso 4: Merge a Main
```bash
# Opción A: Merge directo (para features pequeños)
git checkout main
git merge feat/nueva-funcionalidad
git push origin main

# Opción B: Pull Request (para features grandes)
git push origin feat/nueva-funcionalidad
# Crear PR en GitHub
```

### Paso 5: Cleanup
```bash
# Eliminar branch local
git branch -d feat/nueva-funcionalidad

# Eliminar branch remoto (si existe)
git push origin --delete feat/nueva-funcionalidad
```

---

## 📝 Convenciones de Commits

### Formato
```
<tipo>: <descripción corta>

<descripción detallada opcional>

<footer opcional>
```

### Tipos de Commit

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `feat:` | Nueva funcionalidad | `feat: Add quality presets system` |
| `fix:` | Bug fix | `fix: Resolve cache memory leak` |
| `docs:` | Documentación | `docs: Update API reference` |
| `test:` | Tests | `test: Add cache integration tests` |
| `refactor:` | Refactorización | `refactor: Simplify media service` |
| `perf:` | Optimización | `perf: Improve cache lookup speed` |
| `chore:` | Mantenimiento | `chore: Update dependencies` |

### Ejemplos de Buenos Commits

```bash
# Feature con descripción
git commit -m "feat: Implement Smart Cache System

Added intelligent caching for media assets with:
- SQLite storage backend
- Hash-based exact matching
- Similarity-based fuzzy matching
- Automatic cleanup and statistics"

# Bug fix simple
git commit -m "fix: Handle missing cache directory on init"

# Documentación
git commit -m "docs: Add development workflow guide"
```

---

## 🔀 Estrategias de Merge

### Fast-Forward Merge (Preferido)
Mantiene historia lineal y limpia.

```bash
git checkout main
git merge --ff-only feat/nueva-funcionalidad
```

Si falla, rebase primero:
```bash
git checkout feat/nueva-funcionalidad
git rebase main
git checkout main
git merge feat/nueva-funcionalidad
```

### Merge Commit (Para Features Grandes)
Preserva contexto del feature branch.

```bash
git checkout main
git merge --no-ff feat/nueva-funcionalidad
```

---

## 🎯 Ejemplos de Workflow Completo

### Ejemplo 1: Feature Pequeño (Quality Presets)

```bash
# 1. Crear branch
git checkout -b feat/quality-presets

# 2. Desarrollar
# ... escribir código ...
git add src/config/presets.py
git commit -m "feat: Add quality preset definitions"

# ... más desarrollo ...
git add tests/test_presets.py
git commit -m "test: Add quality preset tests"

# 3. Merge a main
git checkout main
git merge feat/quality-presets

# 4. Push
git push origin main

# 5. Cleanup
git branch -d feat/quality-presets
```

### Ejemplo 2: Bug Fix Urgente

```bash
# 1. Crear branch desde main
git checkout main
git checkout -b fix/cache-crash

# 2. Fix rápido
# ... arreglar bug ...
git add src/services/cache/storage.py
git commit -m "fix: Prevent crash on null cache entry"

# 3. Test
python tests/test_cache.py

# 4. Merge inmediato
git checkout main
git merge fix/cache-crash
git push origin main

# 5. Cleanup
git branch -d fix/cache-crash
```

### Ejemplo 3: Feature Grande con Multiple Commits

```bash
# 1. Crear branch
git checkout -b feat/cost-tracker

# 2. Desarrollo incremental
git commit -m "feat: Add cost tracking database schema"
git commit -m "feat: Implement cost calculation logic"
git commit -m "feat: Add cost tracker API endpoints"
git commit -m "test: Add comprehensive cost tracker tests"
git commit -m "docs: Document cost tracker usage"

# 3. Mantener actualizado con main
git checkout main
git pull origin main
git checkout feat/cost-tracker
git rebase main

# 4. Merge final
git checkout main
git merge --no-ff feat/cost-tracker -m "feat: Implement Cost Tracker System"

# 5. Push y cleanup
git push origin main
git branch -d feat/cost-tracker
```

---

## 🚫 Antipatrones a Evitar

### ❌ NO HACER

1. **Trabajar directo en main para features**
   ```bash
   # ❌ MAL
   git checkout main
   # ... desarrollar feature ...
   git commit -m "feat: new feature"
   ```

2. **Branches con nombres genéricos**
   ```bash
   # ❌ MAL
   git checkout -b test
   git checkout -b fixes
   git checkout -b updates
   ```

3. **Commits masivos sin contexto**
   ```bash
   # ❌ MAL
   git add .
   git commit -m "changes"
   git commit -m "update"
   git commit -m "fix stuff"
   ```

4. **Dejar branches obsoletos**
   ```bash
   # ❌ MAL - nunca limpiar branches viejos
   git branch  # muestra 50+ branches
   ```

### ✅ HACER

1. **Branch específico para cada tarea**
   ```bash
   # ✅ BIEN
   git checkout -b feat/quality-presets
   # ... desarrollar ...
   git merge y cleanup
   ```

2. **Nombres descriptivos**
   ```bash
   # ✅ BIEN
   git checkout -b feat/cost-tracker
   git checkout -b fix/tts-timeout
   git checkout -b docs/api-reference
   ```

3. **Commits atómicos con contexto**
   ```bash
   # ✅ BIEN
   git add src/services/cache/
   git commit -m "feat: Implement cache storage backend"

   git add tests/test_cache.py
   git commit -m "test: Add cache integration tests"
   ```

4. **Cleanup regular**
   ```bash
   # ✅ BIEN
   git branch -d feat/quality-presets  # después de merge
   ```

---

## 📊 Estado de Branches

### Comando Útil: Ver Branches
```bash
# Ver todos los branches locales
git branch

# Ver branches con último commit
git branch -v

# Ver branches mergeados
git branch --merged

# Ver branches NO mergeados
git branch --no-merged
```

### Cleanup de Branches Viejos
```bash
# Ver branches mergeados (seguros de eliminar)
git branch --merged | grep -v "main"

# Eliminar branches mergeados
git branch --merged | grep -v "main" | xargs git branch -d
```

---

## 🎓 Resumen

**Reglas de Oro:**

1. ✅ **SIEMPRE** crear branch para features/bugs
2. ✅ Usar nombres descriptivos con prefijo
3. ✅ Commits frecuentes y atómicos
4. ✅ Tests antes de merge
5. ✅ Cleanup después de merge
6. ✅ Mantener main limpio y estable

**Template Rápido:**
```bash
# Feature nuevo
git checkout -b feat/<nombre>
# ... desarrollo ...
git checkout main && git merge feat/<nombre>
git branch -d feat/<nombre>

# Bug fix
git checkout -b fix/<nombre>
# ... arreglo ...
git checkout main && git merge fix/<nombre>
git branch -d fix/<nombre>
```

---

## 🔗 Referencias

- [Git Branching Best Practices](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

---

**Última actualización:** 2024-11-30
