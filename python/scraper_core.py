#!/usr/bin/env python3
"""
scraper_core.py — Motor de scraping unificado para Portraits-AI.

Lee la configuración de monarcas.json y descarga retratos desde Wikipedia,
con fallback de idioma y filtrado inteligente por keywords.

Uso:
    python scraper_core.py                    # Descarga todas las dinastías
    python scraper_core.py --dynasty Francesa # Solo una dinastía específica
    python scraper_core.py --count            # Solo contar sin descargar
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
import wikipedia

# --- CONFIGURACIÓN GLOBAL ---
BASE_DIR = Path(os.path.abspath(__file__)).parent / "Retratos"
CONFIG_FILE = Path(os.path.abspath(__file__)).parent / "monarcas.json"

HEADERS = {
    "User-Agent": "PortraitsAI/1.0 (https://github.com/NicoRuedaA/Portraits-AI; academic/educational use)"
}

# Límite de imágenes por monarca (evitar rate limits)
MAX_IMAGES_PER_MONARCH = 5

# Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


def load_config() -> dict:
    """Carga la configuración desde monarcas.json."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No se encontró {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    log.info(f"Cargadas {len(config)} dinastías desde {CONFIG_FILE.name}")
    return config


def setup_wikipedia(lang: str):
    """Configura el idioma de Wikipedia API."""
    try:
        wikipedia.set_lang(lang)
    except Exception as e:
        log.warning(f"No se pudo configurar idioma '{lang}': {e}")


def get_valid_images(page_title: str, keywords: list, exclude_keywords: list) -> list:
    """
    Busca imágenes válidas en una página de Wikipedia, filtrando por keywords.

    Args:
        page_title: Título de la página de Wikipedia
        keywords: Palabras clave que DEBE contener la URL
        exclude_keywords: Palabras clave que NO deben estar en la URL

    Returns:
        Lista de URLs de imágenes válidas
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

            # Debe tener AL MENOS UNA keyword positiva
            if keywords and not any(k in img_name for k in keywords):
                continue

            # NO debe tener NINGUNA keyword negativa
            if exclude_keywords and any(k in img_name for k in exclude_keywords):
                continue

            valid_urls.append(img_url)

    except wikipedia.exceptions.PageError:
        log.error(f"Página no encontrada: {page_title}")
    except Exception as e:
        log.error(f"Error accediendo a {page_title}: {e}")

    return valid_urls[:MAX_IMAGES_PER_MONARCH]


def download_image(url: str, ruta_destino: Path, timeout: int = 15) -> bool:
    """
    Descarga una imagen desde una URL.

    Args:
        url: URL de la imagen
        ruta_destino: Ruta donde guardar la imagen
        timeout: Timeout en segundos para el request

    Returns:
        True si se descargó correctamente, False en caso contrario
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        if response.status_code == 200:
            ruta_destino.parent.mkdir(parents=True, exist_ok=True)
            with open(ruta_destino, "wb") as f:
                f.write(response.content)
            return True
    except requests.exceptions.Timeout:
        log.error(f"Timeout descargando {url}")
    except requests.exceptions.RequestException as e:
        log.error(f"Error descargando {url}: {e}")
    except Exception as e:
        log.error(f"Error inesperada descargando {url}: {e}")

    return False


def download_monarch_portraits(
    monarch: list, dynasty: str, config_dynasty: dict, verbose: bool = True
) -> dict:
    """
    Descarga los retratos de un monarca.

    Args:
        monarch: [nombre, inicio, fin, siglo]
        dynasty: Nombre de la dinastía
        config_dynasty: Configuración específica de la dinastía (keywords, lang, etc.)
        verbose: Si True, imprime progreso

    Returns:
        Dict con estadísticas: {'monarch': str, 'downloaded': int, 'skipped': int, 'error': str or None}
    """
    nombre, inicio, fin, siglo = monarch
    lang = config_dynasty.get("lang", "es")
    fallback_lang = config_dynasty.get("fallback_lang", "en")
    keywords = config_dynasty.get("keywords", [])
    exclude_keywords = config_dynasty.get("exclude_keywords", [])

    result = {"monarch": nombre, "downloaded": 0, "skipped": 0, "error": None}

    # Crear estructura de carpetas: Retratos/Siglo/Dinastía/Monarca (Años)
    carpeta_nombre = f"{nombre} {inicio}-{fin}"
    ruta_base = BASE_DIR / siglo / dynasty / carpeta_nombre

    if verbose:
        log.info(f"Buscando portraits para: {nombre} ({siglo}/{dynasty})")

    # Intentar en el idioma principal
    setup_wikipedia(lang)
    urls = get_valid_images(nombre, keywords, exclude_keywords)

    # Si no hay imágenes, intentar con fallback
    if not urls and fallback_lang and fallback_lang != lang:
        if verbose:
            log.info(f"  Fallback a {fallback_lang} para {nombre}")
        setup_wikipedia(fallback_lang)
        urls = get_valid_images(nombre, keywords, exclude_keywords)

    if not urls:
        if verbose:
            log.warning(f"  No se encontraron imágenes válidas para {nombre}")
        result["skipped"] = 1
        return result

    # Descargar cada URL válida
    for i, url in enumerate(urls[:MAX_IMAGES_PER_MONARCH]):
        extension = url.split(".")[-1].lower()
        if extension not in ("jpg", "jpeg", "png"):
            extension = "jpg"

        nombre_archivo = f"{nombre} {inicio}-{fin}_{i + 1}.{extension}"
        ruta_final = ruta_base / nombre_archivo

        if ruta_final.exists():
            if verbose:
                log.info(f"  [SKIP] Ya existe: {nombre_archivo}")
            result["skipped"] += 1
            continue

        if download_image(url, ruta_final):
            if verbose:
                log.info(f"  [OK] Guardado: {nombre_archivo}")
            result["downloaded"] += 1
            time.sleep(1)  # Respetar rate limits
        else:
            result["skipped"] += 1

    return result


def process_dynasty(
    dynasty_name: str, dynasty_config: dict, verbose: bool = True
) -> dict:
    """
    Procesa todos los monarcas de una dinastía.

    Args:
        dynasty_name: Nombre de la dinastía
        dynasty_config: Configuración de la dinastía
        verbose: Si True, imprime progreso

    Returns:
        Dict con estadísticas agregadas de la dinastía
    """
    stats = {
        "dynasty": dynasty_name,
        "monarchs_processed": 0,
        "monarchs_skipped": 0,
        "images_downloaded": 0,
        "images_skipped": 0,
        "errors": [],
    }

    monarcas = dynasty_config.get("monarcas", [])

    if not monarcas:
        log.warning(f"Dinastía {dynasty_name} no tiene monarcas definidos")
        return stats

    log.info(f"Procesando dinastía: {dynasty_name} ({len(monarcas)} monarcas)")

    for monarch in monarcas:
        result = download_monarch_portraits(
            monarch, dynasty_name, dynasty_config, verbose
        )

        if result["downloaded"] > 0:
            stats["monarchs_processed"] += 1
        elif result["skipped"] > 0:
            stats["monarchs_skipped"] += 1

        stats["images_downloaded"] += result["downloaded"]
        stats["images_skipped"] += result["skipped"]

        if result["error"]:
            stats["errors"].append(result["error"])

    return stats


def count_portraits() -> dict:
    """Cuenta los retratos existentes en el dataset."""
    stats = {"total_images": 0, "by_dynasty": {}, "by_century": {}}

    if not BASE_DIR.exists():
        return stats

    for siglo_dir in BASE_DIR.iterdir():
        if not siglo_dir.is_dir() or siglo_dir.name.startswith("."):
            continue

        if siglo_dir.name == "00_DESCARTADOS" or siglo_dir.name == "01_RECORTE_FINAL":
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


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Motor de scraping unificado para Portraits-AI"
    )
    parser.add_argument(
        "--dynasty", "-d", type=str, help="Solo procesar una dinastía específica"
    )
    parser.add_argument(
        "--count",
        "-c",
        action="store_true",
        help="Solo contar las imágenes existentes, sin descargar",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Reducir output")

    args = parser.parse_args()

    verbose = not args.quiet

    if args.count:
        # Modo conteo
        stats = count_portraits()
        print(f"\n=== ESTADO DEL DATASET ===")
        print(f"Total de imágenes: {stats['total_images']}")
        print(f"\nPor dinastía:")
        for dyn, count in sorted(stats["by_dynasty"].items()):
            print(f"  {dyn}: {count}")
        print(f"\nPor siglo:")
        for siglo, count in sorted(stats["by_century"].items()):
            print(f"  {siglo}: {count}")
        return

    # Cargar configuración
    config = load_config()

    if args.dynasty:
        # Solo una dinastía
        if args.dynasty not in config:
            log.error(f"Dinastía '{args.dynasty}' no encontrada en configuración")
            log.info(f"Dinastías disponibles: {', '.join(config.keys())}")
            sys.exit(1)

        dynasty_config = config[args.dynasty]
        stats = process_dynasty(args.dynasty, dynasty_config, verbose)

        print(f"\n=== RESULTADO: {args.dynasty} ===")
        print(f"Monarcas procesados: {stats['monarchs_processed']}")
        print(f"Monarcas sin imágenes: {stats['monarchs_skipped']}")
        print(f"Imágenes descargadas: {stats['images_downloaded']}")
        print(f"Imágenes saltadas/existentes: {stats['images_skipped']}")
    else:
        # Todas las dinastías
        total_stats = {
            "total_dynasties": len(config),
            "monarchs_processed": 0,
            "monarchs_skipped": 0,
            "images_downloaded": 0,
            "images_skipped": 0,
        }

        for dynasty_name, dynasty_config in config.items():
            log.info(f"\n=== Procesando: {dynasty_name} ===")
            stats = process_dynasty(dynasty_name, dynasty_config, verbose)

            total_stats["monarchs_processed"] += stats["monarchs_processed"]
            total_stats["monarchs_skipped"] += stats["monarchs_skipped"]
            total_stats["images_downloaded"] += stats["images_downloaded"]
            total_stats["images_skipped"] += stats["images_skipped"]

        print(f"\n=== RESULTADO FINAL ===")
        print(f"Dinastías procesadas: {total_stats['total_dynasties']}")
        print(f"Monarcas con imágenes: {total_stats['monarchs_processed']}")
        print(f"Monarcas sin imágenes: {total_stats['monarchs_skipped']}")
        print(f"Imágenes descargadas: {total_stats['images_downloaded']}")
        print(f"Imágenes saltadas/existentes: {total_stats['images_skipped']}")


if __name__ == "__main__":
    main()
