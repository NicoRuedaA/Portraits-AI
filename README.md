# Portraits AI: Sistema de Procesamiento de Retratos Históricos

Este proyecto automatiza la descarga, limpieza y estandarización de retratos históricos para su uso en videojuegos (como CK3) o aplicaciones educativas.

## Estructura del Proyecto
- `Retratos/`: Directorio principal de imágenes.
  - `00_DESCARTADOS/`: Imágenes que no cumplen los requisitos.
  - `01_RECORTE_FINAL/`: Retratos procesados (512x768).
  - `Python/`: Scripts de procesamiento de imágenes.
- `python/`: Scripts de descarga (scrapers) y utilidades.
  - `scraper_core.py`: Motor unificado para descargar desde Wikipedia.
- `requirements.txt`: Dependencias del proyecto.

## Instalación
1. Asegúrate de tener Python 3.10+ instalado.
2. Crea un entorno virtual: `python -m venv venv`
3. Instala las dependencias: `pip install -r requirements.txt`

## Uso
1. **Descarga**: Configura los monarcas en `python/scraper_core.py` y ejecútalo para poblar la carpeta `Retratos/`.
2. **Procesamiento**: Ejecuta `Retratos/Python/recortar_retratos.py` para realizar el recorte inteligente y las mejoras visuales.

## Mejoras Implementadas
- **Detección Facial Inteligente**: Fallback automático si no se detecta rostro.
- **Mejora Visual**: Ajuste automático de brillo, contraste y nitidez para óleos.
- **Organización Automática**: Mantiene la jerarquía Siglo/Dinastía/Monarca.
