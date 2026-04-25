#!/usr/bin/env python3
"""
scraper_core.py — Motor de scraping unificado para Portraits-AI.

Lee la configuración de monarcas.json y descarga retratos desde Wikipedia,
con fallback de idioma, retry con backoff y logging estructurado.

Uso:
    python scraper_core.py                    # Descarga todas las dinastías
    python scraper_core.py --dynasty Francesa # Solo una dinastía específica
    python scraper_core.py --count            # Solo contar sin descargar
    python scraper_core.py --verbose          # Log detallado a archivo
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import wikipedia

# --- CONFIGURACIÓN GLOBAL ---
BASE_DIR = Path(os.path.abspath(__file__)).parent / "Retratos"
CONFIG_FILE = Path(os.path.abspath(__file__)).parent / "monarcas.json"
LOG_DIR = Path(os.path.abspath(__file__)).parent / "logs"

HEADERS = {
    "User-Agent": "PortraitsAI/1.0 (https://github.com/NicoRuedaA/Portraits-AI; academic/educational use)"
}

# Límite de imágenes por monarca
MAX_IMAGES_PER_MONARCH = 5

# Configuración de retry
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # segundos (2, 4, 8)
REQUEST_TIMEOUT = 15

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, log_file: Path = None):
    """
    Configura logging estructurado a archivo + consola.

    Args:
        verbose: Si True, nivel DEBUG
        log_file: Ruta personalizada para el log
    """
    global log

    # Crear directorio de logs si no existe
    LOG_DIR.mkdir(exist_ok=True)

    # Nombre de archivo por fecha
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOG_DIR / f"portraits_{timestamp}.log"

    # Configurar logger raíz
    _log_level = logging.DEBUG if verbose else logging.INFO  # noqa: F841

    # File handler (todo)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(funcName)s | %(message)s"
    )
    file_handler.setFormatter(file_format)

    # Console handler (info+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_format)

    # Agregar handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    log = logging.getLogger(__name__)
    log.info(f"Logging configurado: {log_file}")

    return log_file


def load_config() -> dict:
    """Carga la configuración desde monarcas.json."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No se encontró {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    log.info(f"Cargadas {len(config)} dinastías desde {CONFIG_FILE.name}")
    return config


def setup_wikipedia(lang: str) -> bool:
    """
    Configura el idioma de Wikipedia API.

    Args:
        lang: Código de idioma (es, en, fr, etc.)

    Returns:
        True si se configuró correctamente
    """
    try:
        wikipedia.set_lang(lang)
        return True
    except Exception as e:
        log.warning(f"No se pudo configurar idioma '{lang}': {e}")
        return False


def download_with_retry(
    url: str, ruta_destino: Path, timeout: int = REQUEST_TIMEOUT
) -> dict:
    """
    Descarga una imagen con retry y backoff exponencial.

    Args:
        url: URL de la imagen
        ruta_destino: Ruta donde guardar la imagen
        timeout: Timeout en segundos

    Returns:
        Dict con {'success': bool, 'error': str or None, 'attempts': int}
    """
    result = {"success": False, "error": None, "attempts": 0}

    for attempt in range(1, MAX_RETRIES + 1):
        result["attempts"] = attempt

        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)

            if response.status_code == 200:
                ruta_destino.parent.mkdir(parents=True, exist_ok=True)
                with open(ruta_destino, "wb") as f:
                    f.write(response.content)
                result["success"] = True
                log.debug(f"Descargado en intento {attempt}: {url}")
                break
            elif response.status_code == 429:
                # Rate limited - esperar más
                wait_time = RETRY_BACKOFF_BASE * (2**attempt)
                log.warning(f"Rate limited (429). Esperando {wait_time}s...")
                time.sleep(wait_time)
            else:
                result["error"] = f"HTTP {response.status_code}"
                log.warning(f"HTTP error {response.status_code}: {url}")

        except requests.exceptions.Timeout:
            result["error"] = "Timeout"
            log.warning(f"Timeout (intento {attempt}/{MAX_RETRIES}): {url}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
            log.warning(f"Request error (intento {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

        except Exception as e:
            result["error"] = f"Unexpected: {e}"
            log.error(f"Error inesperada: {e}")
            break

    return result


def get_valid_images(page_title: str, keywords: list, exclude_keywords: list) -> list:
    """
    Busca imágenes válidas en una página de Wikipedia.

    Args:
        page_title: Título de la página
        keywords: Palabras clave requeridas
        exclude_keywords: Palabras clave a excluir

    Returns:
        Lista de URLs válidas
    """
    valid_urls = []

    try:
        page = wikipedia.page(page_title, auto_suggest=False)
        images = page.images or []

        for img_url in images:
            img_name = img_url.lower()

            # Filtrar por extensión
            if not any(img_name.endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
                continue

            # Keyword positiva requerida
            if keywords and not any(k in img_name for k in keywords):
                continue

            # Keywords negativas
            if exclude_keywords and any(k in img_name for k in exclude_keywords):
                continue

            valid_urls.append(img_url)

    except wikipedia.exceptions.PageError:
        log.debug(f"Página no encontrada: {page_title}")
    except Exception as e:
        log.debug(f"Error accediendo a {page_title}: {e}")

    return valid_urls[:MAX_IMAGES_PER_MONARCH]


def download_monarch_portraits(
    monarch: list, dynasty: str, config_dynasty: dict, stats: dict
) -> dict:
    """
    Descarga los retratos de un monarca con retry y fallback de idioma.

    Args:
        monarch: [nombre, inicio, fin, siglo]
        dynasty: Nombre de la dinastía
        config_dynasty: Config de la dinastía
        stats: Dict de estadísticas acumuladas

    Returns:
        Dict con resultado
    """
    nombre, inicio, fin, siglo = monarch
    lang = config_dynasty.get("lang", "es")
    fallback_lang = config_dynasty.get("fallback_lang", "en")
    keywords = config_dynasty.get("keywords", [])
    exclude_keywords = config_dynasty.get("exclude_keywords", [])

    result = {
        "monarch": nombre,
        "dynasty": dynasty,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "errors": [],
    }

    # Crear estructura de carpetas
    carpeta_nombre = f"{nombre} {inicio}-{fin}"
    ruta_base = BASE_DIR / siglo / dynasty / carpeta_nombre

    log.info(f"Buscando: {nombre} ({siglo}/{dynasty})")

    # Intentar en idioma principal
    urls = []
    langs_tried = [lang]

    if setup_wikipedia(lang):
        urls = get_valid_images(nombre, keywords, exclude_keywords)

    # Fallback si no hay imágenes
    if not urls and fallback_lang and fallback_lang != lang:
        langs_tried.append(fallback_lang)
        if setup_wikipedia(fallback_lang):
            urls = get_valid_images(nombre, keywords, exclude_keywords)

        # Último intento: inglés (siempre disponible)
        if not urls and fallback_lang != "en" and lang != "en":
            langs_tried.append("en")
            if setup_wikipedia("en"):
                urls = get_valid_images(nombre, keywords, exclude_keywords)

    if not urls:
        log.warning(f"Sin imágenes para {nombre} (probados: {', '.join(langs_tried)})")
        stats["monarchs_empty"] += 1
        result["skipped"] = 1
        return result

    # Descargar cada URL
    downloaded_count = 0

    for i, url in enumerate(urls[:MAX_IMAGES_PER_MONARCH]):
        extension = url.split(".")[-1].lower()
        if extension not in ("jpg", "jpeg", "png"):
            extension = "jpg"

        nombre_archivo = f"{nombre} {inicio}-{fin}_{i + 1}.{extension}"
        ruta_final = ruta_base / nombre_archivo

        if ruta_final.exists():
            log.info(f"  [EXISTS] {nombre_archivo}")
            result["skipped"] += 1
            continue

        # Descargar con retry
        download_result = download_with_retry(url, ruta_final)

        if download_result["success"]:
            log.info(f"  [OK] {nombre_archivo}")
            result["downloaded"] += 1
            downloaded_count += 1
            stats["images_downloaded"] += 1
            time.sleep(1)  # Rate limit
        else:
            log.warning(f"  [FAIL] {nombre_archivo}: {download_result['error']}")
            result["failed"] += 1
            result["errors"].append(download_result["error"])
            stats["images_failed"] += 1

    if downloaded_count > 0:
        stats["monarchs_with_images"] += 1

    return result


def process_dynasty(dynasty_name: str, dynasty_config: dict, stats: dict) -> dict:
    """
    Procesa todos los monarcas de una dinastía.

    Args:
        dynasty_name: Nombre de la dinastía
        dynasty_config: Config de la dinastía
        stats: Dict de estadísticas

    Returns:
        Dict con resultados de la dinastía
    """
    monarcas = dynasty_config.get("monarcas", [])

    if not monarcas:
        log.warning(f"Dinastía {dynasty_name} sin monarcas")
        return {"dynasty": dynasty_name, "results": []}

    log.info(f"{dynasty_name}: {len(monarcas)} monarcas")

    results = []

    for monarch in monarcas:
        result = download_monarch_portraits(
            monarch, dynasty_name, dynasty_config, stats
        )
        results.append(result)

    return {"dynasty": dynasty_name, "results": results}


def count_portraits() -> dict:
    """Cuenta los retratos existentes."""
    stats = {"total_images": 0, "by_dynasty": {}, "by_century": {}}

    if not BASE_DIR.exists():
        return stats

    for siglo_dir in BASE_DIR.iterdir():
        if not siglo_dir.is_dir():
            continue
        if siglo_dir.name.startswith("."):
            continue
        if siglo_dir.name in ("00_DESCARTADOS", "01_RECORTE_FINAL", "Python"):
            continue

        siglo_name = siglo_dir.name

        for dyn_dir in siglo_dir.iterdir():
            if not dyn_dir.is_dir():
                continue

            dyn_name = dyn_dir.name

            count = sum(
                1
                for f in dyn_dir.rglob("*")
                if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png")
            )

            if count > 0:
                stats["total_images"] += count
                stats["by_dynasty"][dyn_name] = (
                    stats["by_dynasty"].get(dyn_name, 0) + count
                )
                stats["by_century"][siglo_name] = (
                    stats["by_century"].get(siglo_name, 0) + count
                )

    return stats


def print_summary(stats: dict, log_file: Path):
    """Imprime resumen final."""
    print("\n" + "=" * 50)
    print("RESUMEN DE DESCARGA")
    print("=" * 50)
    print(f"Dinastías procesadas: {stats['dynasties_processed']}")
    print(f"Monarcas con imágenes: {stats['monarchs_with_images']}")
    print(f"Monarcas sin imágenes: {stats['monarchs_empty']}")
    print(f"Imágenes descargadas: {stats['images_downloaded']}")
    print(f"Imágenes fallidas: {stats['images_failed']}")
    print("=" * 50)
    print(f"Log: {log_file}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description="Motor de scraping Portraits-AI")
    parser.add_argument("--dynasty", "-d", type=str, help="Dinastía específica")
    parser.add_argument("--count", "-c", action="store_true", help="Contar imágenes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log detallado")
    parser.add_argument("--quiet", "-q", action="store_true", help="Reducir output")
    parser.add_argument("--log", type=str, help="Archivo de log personalizado")

    args = parser.parse_args()

    # Setup logging
    log_file = None
    if args.log:
        log_file = Path(args.log)
    else:
        log_file = setup_logging(verbose=args.verbose)

    # Inicializar stats
    stats = {
        "dynasties_processed": 0,
        "monarchs_with_images": 0,
        "monarchs_empty": 0,
        "images_downloaded": 0,
        "images_failed": 0,
    }

    # === MODO CONTEO ===
    if args.count:
        count_stats = count_portraits()
        print("\n=== ESTADO DEL DATASET ===")
        print(f"Total: {count_stats['total_images']}")
        print("\nPor dinastía:")
        for dyn, count in sorted(count_stats["by_dynasty"].items()):
            print(f"  {dyn}: {count}")
        print("\nPor siglo:")
        for siglo, count in sorted(count_stats["by_century"].items()):
            print(f"  {siglo}: {count}")
        return

    # === MODO DESCARGA ===
    config = load_config()

    if args.dynasty:
        # Solo una dinastía
        if args.dynasty not in config:
            log.error(f"Dinastía '{args.dynasty}' no encontrada")
            log.info(f"Disponibles: {', '.join(config.keys())}")
            sys.exit(1)

        log.info(f"=== {args.dynasty} ===")
        process_dynasty(args.dynasty, config[args.dynasty], stats)
        stats["dynasties_processed"] = 1
    else:
        # Todas las dinastías
        for dynasty_name, dynasty_config in config.items():
            log.info(f"\n=== {dynasty_name} ===")
            process_dynasty(dynasty_name, dynasty_config, stats)
            stats["dynasties_processed"] += 1

    # Resumen final
    print_summary(stats, log_file)


if __name__ == "__main__":
    main()
