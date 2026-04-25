# Portraits-AI: Roadmap de Refactorización

> Última actualización: Abril 2026
> Estado actual: Pipeline funcional pero con deuda técnica crítica

---

## Visión del Proyecto

Un sistema robusto y extensible para descargar, filtrar y estandarizar retratos históricos
desde Wikipedia, generando un dataset organizado listo para entrenamiento de modelos (LoRA)
o uso en videojuegos (CK3) / aplicaciones educativas.

---

## Fase 0 — Estabilizar lo que hay (sin romper nada)

> **Objetivo**: Garantizar que el repo esté limpio y lo actual no se pierda.

### 0.1 Crear `.gitignore`

Excluir los archivos que NO deben trackearse:

```
# Imágenes (se regeneran del pipeline)
*.jpg
*.jpeg
*.png
!Retratos/**/*
!01_RECORTE_FINAL/**/*

# O mejor: trackear solo código y config, no datos
Retratos/Siglo*/
Retratos/00_DESCARTADOS/
01_RECORTE_FINAL/
*.whl
venv/
__pycache__/
*.pyc
.env
```

**Decisión clave**: ¿Trackear imágenes en git? Para un dataset, la respuesta debería ser **NO**. Usar Git LFS o almacenamiento externo si necesitás versionar las imágenes.

### 0.2 Commit de estabilización

- Eliminar `numpy-2.3.4-cp314-cp314-win_amd64.whl` de `Retratos/`
- Limpiar `__pycache__/` de todo el proyecto
- Verificar que `requirements.txt` cubre todas las dependencias reales

### 0.3 Verificar que el pipeline actual funciona

- Ejecutar `main.py` end-to-end con los datos existentes
- Confirmar que descarga + recorte funciona
- Documentar cualquier falla real

---

## Fase 1 — Eliminar Duplicación (LA PRIORIDAD MÁXIMA)

> **Objetivo**: Un solo motor de scraping, un solo archivo de datos.
> **Impacto**: De 14+ archivos duplicados → 1 motor + 1 config.

### 1.1 Expandir `monarcas.json` con TODAS las dinastías

Consolidar las listas hardcodeadas de los 7 scripts individuales en un único JSON:

```json
{
  "Española": {
    "lang": "es",
    "keywords": ["portrait", "painting", "king", "queen", "rey", "reina", "retrato", "monarch"],
    "exclude_keywords": ["arms", "coa", "map", "flag", "svg", "castle", "mapa", "familia", "palace"],
    "monarcas": [
      ["Enrique II de Castilla", 1369, 1379, "Siglo XIV"],
      ...
    ]
  },
  "Británica": { ... },
  "Francesa": { ... },
  "Otomana": { ... },
  "Rusa": { ... },
  "Ming": { ... },
  "Qing": { ... },
  "Mogol": { ... },
  "Japonesa": { ... },
  "Danesa": { ... },
  "Etiopía": { ... }
}
```

Cada dinastía define:
- `lang`: idioma de búsqueda en Wikipedia
- `keywords` / `exclude_keywords`: filtros específicos por cultura
- `fallback_lang`: idioma alternativo si la búsqueda principal falla (nuevo!)

### 1.2 Refactorizar `scraper_core.py` como motor único

Eliminar TODOS los `descargar_retratos_*.py` individuales. `scraper_core.py` ya tiene la firma correcta:

```python
def procesar_monarcas(lista_monarcas, dinastia_nombre, lang="es"):
```

Mejoras necesarias:
- ✅ Ya usa `os.getcwd()` en vez de path hardcoded
- ❌ Agregar: keywords/excludes por dinastía (leer del JSON)
- ❌ Agregar: fallback de idioma (es → en si falla)
- ❌ Agregar: límite de imágenes por monarca (ya existe `[:5]`)
- ❌ Agregar: escribir resultados en CSV/log

### 1.3 Eliminar `Retratos/Python/` (duplicado exacto de `python/`)

Mover los scripts únicos a `python/`:
- `recortar_retratos.py` → `python/recortar_retratos.py`
- `eliminar_corruptos.py` → `python/eliminar_corruptos.py`

Eliminar toda la carpeta `Retratos/Python/`.

### 1.4 Nueva estructura de archivos resultante

```
Portraits-AI/
├── main.py                    ← CLI unificado (refactorizado en Fase 2)
├── monarcas.json              ← TODAS las dinastías + config
├── requirements.txt
├── ROADMAP.md
├── .gitignore
├── python/
│   ├── scraper_core.py        ← Motor único de scraping (refactorizado)
│   ├── recortar_retratos.py   ← Procesamiento de imágenes
│   ├── eliminar_corruptos.py  ← Filtrado de imágenes
│   ├── contar_archivos.py     ← Utility
│   └── eliminar_carpetas.py  ← Utility
├── Retratos/                  ← Dataset (generado, no trackeado)
│   ├── Siglo XIV/
│   ├── ...
│   └── 00_DESCARTADOS/
└── 01_RECORTE_FINAL/          ← Output final (generado)
```

---

## Fase 2 — Robustecer el Motor

> **Objetivo**: Que el sistema funcione sin supervisión y reporte resultados claros.

### 2.1 CLI con `argparse` en `main.py`

```python
python main.py --download --dynasty Francesa
python main.py --download --all
python main.py --process
python main.py --filter
python main.py --count
python main.py --full          # download + filter + process
```

### 2.2 Sistema de Logging Estructurado

Reemplazar todos los `print()` con logging configurado:
- `--verbose` / `--quiet` flags
- Log file: `portraits_YYYYMMDD.log`
- CSV de resultados: `monarca,estado,urls_encontradas,urls_descargadas,error`

### 2.3 Manejo de Errores mejorado

- Retry con backoff exponencial (3 intentos) para requests fallidas
- Timeout configurable (default 15s)
- Reporte final: "X monarcas procesados, Y fallidos, Z sin imágenes"
- No abortar todo el pipeline si un monarca falla

### 2.4 Fallback de Idioma en scraper_core

Los scripts de Asia/África ya intentaban `es → en` como fallback.
Incorporar esto en `scraper_core.py` de forma configurable:

```python
def procesar_monarcas(lista_monarcas, dinastia_nombre, lang="es", fallback_lang="en"):
```

---

## Fase 3 — Tests y Calidad

> **Objetivo**: Confianza en el código. Poder refactorizar sin miedo.

### 3.1 Tests Unitarios

```
tests/
├── test_scraper_core.py    ← Mock de Wikipedia API
├── test_filtrado.py        ← Keywords/include/exclude
├── test_recorte.py         ← Detección facial + resize
└── test_config.py          ← Validación de monarcas.json
```

Casos críticos a testear:
- Filtrado de URLs (keywords positivas + excludes)
- Detección facial con fallback a centro
- Conversión RGBA → RGB
- Cálculo del crop box
- Validación del schema de `monarcas.json`

### 3.2 Schema Validation para `monarcas.json`

Con `jsonschema` o `pydantic`:

```python
DYNASTY_SCHEMA = {
    "type": "object",
    "required": ["lang", "monarcas"],
    "properties": {
        "lang": {"type": "string", "enum": ["es", "en", "fr", "de", ...]},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "exclude_keywords": {"type": "array", "items": {"type": "string"}},
        "fallback_lang": {"type": "string"},
        "monarcas": {
            "type": "array",
            "items": {
                "type": "array",
                "items": [{"type": "string"}, {"type": "integer"}, {"type": "integer"}, {"type": "string"}],
                "minItems": 4, "maxItems": 4
            }
        }
    }
}
```

### 3.3 Linting y Formato

- `ruff` o `black` para formateo
- `mypy` para type hints
- Pre-commit hooks

---

## Fase 4 — Mejoras del Pipeline de Imágenes

> **Objetivo**: Mejor calidad de retratos en el output final.

### 4.1 Mejoras en Detección Facial

- Agregar modelos alternativos: `haarcascade_frontalface_alt2.xml`, `lbpcascade_frontalface.xml`
- Usar `dlib` o `mediapipe` como fallback más robusto que Haar
- Priorizar rostros frontales sobre.perfil
- Detectar rostros múltiples y seleccionar el más grande/centrado

### 4.2 Mejoras en Recorte

- Aspect ratio configurable (actualmente 512x768 hardcodeado = 2:3)
- Padding configurable alrededor del rostro
- Detección de calidad: descartar imágenes < 300x300px o demasiado borrosas
- Output en formato sin pérdida (PNG) + JPEG para LoRA

### 4.3 Filtrado Inteligente de URLs

Los keywords actuales son rudimentarios. Mejoras:
- Priorizar URLs que contengan el nombre del monarca
- Excluir imágenes < 200px de ancho (imágenes de iconos/escudos pequeños)
- Excluir imágenes SVG (ya se hace parcialmente)
- Scoring de relevancia: `nombre_monarca + portrait` > `painting` solo

---

## Fase 5 — Extensibilidad y Nuevas Fuentes

> **Objetivo**: No depender solo de Wikipedia.

### 5.1 Arquitectura de Providers

```python
class PortraitProvider(ABC):
    @abstractmethod
    def search(self, monarch: Monarch) -> list[str]: ...

class WikipediaProvider(PortraitProvider): ...
class Wikimedia CommonsProvider(PortraitProvider): ...
class BritannicaProvider(PortraitProvider): ...  # futuro
```

### 5.2 Wikimedia Commons API

- Los retratos mejores suelen estar en Commons, no en Wikipedia directamente
- La API de Commons permite filtrar por resolución, tipo, categoría
- Higher quality images lo más probable

### 5.3 Configuración de Fuentes por Dinastía

Algunas dinastías (Mogol, Etíope) tienen mejor cobertura en inglés. Otras (Española, Francesa) en su idioma nativo. Hacer esto configurable:

```json
{
  "Mogol": {
    "lang": "en",
    "fallback_lang": "es",
    "source_priority": ["wikimedia", "wikipedia"]
  }
}
```

---

## Fase 6 — Dataset y Modelado

> **Objetivo**: Dataset listo para entrenamiento.

### 6.1 Metadata por Imagen

Para cada retrato procesado, generar un JSON sidecar:

```json
{
  "monarch": "Luis XIV de Francia",
  "dynasty": "Francesa",
  "reign": "1643-1715",
  "source_url": "https://upload.wikimedia.org/...",
  "source_page": "https://es.wikipedia.org/wiki/Luis_XIV",
  "detection_method": "haar_frontal",
  "crop_box": [120, 50, 380, 430],
  "original_size": [800, 1000],
  "final_size": [512, 768],
  "enhancements": {"brightness": 1.05, "contrast": 1.1, "sharpness": 1.2}
}
```

### 6.2 Dataset Splits

Para entrenamiento LoRA:
- Train (80%) / Validation (10%) / Test (10%)
- Estratificado por dinastía para balance

### 6.3 Data Augmentation Preparación

- Recortes múltiples por imagen (variaciones de zoom/crop)
- Diferentes escalas para robustez

---

## Timeline Estimado

| Fase | Duración | Dificultad | Impacto |
|------|----------|------------|----------|
| **Fase 0** — Estabilizar | 1-2 horas | ⭐ | 🔴 Crítico |
| **Fase 1** — Eliminar Duplicación | 3-4 horas | ⭐⭐ | 🔴 Crítico |
| **Fase 2** — Robustecer Motor | 3-4 horas | ⭐⭐ | 🟡 Alto |
| **Fase 3** — Tests y Calidad | 4-5 horas | ⭐⭐ | 🟡 Alto |
| **Fase 4** — Mejoras Pipeline | 3-4 horas | ⭐⭐⭐ | 🟢 Medio |
| **Fase 5** — Extensibilidad | 5-6 horas | ⭐⭐⭐ | 🟢 Futuro |
| **Fase 6** — Dataset/Modelado | 4-5 horas | ⭐⭐ | 🟢 Futuro |

---

## Principios Guía

1. **DATOS FUERA DEL CÓDIGO**: Toda configuración en JSON/YAML, nunca hardcodeada.
2. **UN SOLO MOTOR**: Una función hace el trabajo, los datos la parametrizan.
3. **PIPELINE IDEMPOTENTE**: Poder ejecutar cualquier fase sin romper las demás.
4. **REPORTAR TODO**: Cada ejecución genera un resumen de qué hizo, qué falló, y cuánto.
5. **GIT LIMPIO**: Solo código y config. Los datos se regeneran del pipeline.