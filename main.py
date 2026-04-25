#!/usr/bin/env python3
"""
main.py — Punto de entrada unificado para Portraits-AI.

Orchestrates el flujo completo:
1. Descarga de retratos desde Wikipedia (scraper_core.py)
2. Procesamiento de imágenes (recortar_retratos.py)

Uso:
    python main.py                    # Pipeline completo
    python main.py --download       # Solo descargar
    python main.py --process        # Solo procesar imágenes
    python main.py --count         # Contar imágenes existentes
    python main.py --dynasty Francesa # Solo dinastía específica
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Añadir script al PATH
BASE_PATH = Path(__file__).parent
sys.path.append(str(BASE_PATH / "python"))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Portraits-AI: Sistema de procesamiento de retratos históricos"
    )

    # Flags de fase
    parser.add_argument(
        "--download",
        "-d",
        action="store_true",
        help="Ejecutar fase de descarga de retratos",
    )
    parser.add_argument(
        "--process",
        "-p",
        action="store_true",
        help="Ejecutar fase de procesamiento de imágenes",
    )
    parser.add_argument(
        "--count", "-c", action="store_true", help="Contar imágenes en el dataset"
    )

    # Opciones adicionales
    parser.add_argument(
        "--dynasty", type=str, help="Solo procesar una dinastía específica"
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Ejecutar todas las fases (default si no se especifica ninguna)",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Reducir output")

    args = parser.parse_args()

    # Si no se especifica ninguna fase, ejecutar todo
    if not (args.download or args.process or args.count):
        args.all = True

    # === FASE 0: Contar (si se solicita) ===
    if args.count:
        from scraper_core import count_portraits

        stats = count_portraits()
        print(f"\n=== ESTADO DEL DATASET ===")
        print(f"Total de imágenes: {stats['total_images']}")
        if stats["by_dynasty"]:
            print(f"\nPor dinastía:")
            for dyn, count in sorted(stats["by_dynasty"].items()):
                print(f"  {dyn}: {count}")
        if stats["by_century"]:
            print(f"\nPor siglo:")
            for siglo, count in sorted(stats["by_century"].items()):
                print(f"  {siglo}: {count}")
        return

    # === FASE 1: Descarga ===
    if args.all or args.download:
        from scraper_core import load_config, process_dynasty

        if not (BASE_PATH / "monarcas.json").exists():
            log.error("No se encontró monarcas.json")
            sys.exit(1)

        config = load_config()

        if args.dynasty:
            # Solo una dinastía
            if args.dynasty not in config:
                log.error(f"Dinastía '{args.dynasty}' no encontrada")
                log.info(f"Disponibles: {', '.join(config.keys())}")
                sys.exit(1)

            log.info(f"\n=== DESCARGANDO: {args.dynasty} ===")
            stats = process_dynasty(
                args.dynasty, config[args.dynasty], verbose=not args.quiet
            )

            print(f"\n=== RESULTADO: {args.dynasty} ===")
            print(f"Monarcas con imágenes: {stats['monarchs_processed']}")
            print(f"Imágenes descargadas: {stats['images_downloaded']}")
        else:
            # Todas las dinastías
            log.info("\n=== FASE 1: DESCARGA DE RETRATOS ===")

            total = {"downloaded": 0, "skipped": 0, "processed": 0}

            for dyn_name, dyn_config in config.items():
                log.info(f"\n>> {dyn_name}")
                stats = process_dynasty(dyn_name, dyn_config, verbose=not args.quiet)

                total["downloaded"] += stats["images_downloaded"]
                total["skipped"] += stats["images_skipped"]
                total["processed"] += stats["monarchs_processed"]

            print(f"\n=== DESCARGAS COMPLETADAS ===")
            print(f"Total imágenes descargadas: {total['downloaded']}")
            print(f"Total imágenes saltadas: {total['skipped']}")

    # === FASE 2: Procesamiento de imágenes ===
    if args.all or args.process:
        from recortar_retratos import procesar_recorte_inteligente

        log.info("\n=== FASE 2: RECORTE Y MEJORA VISUAL ===")

        try:
            procesar_recorte_inteligente()
        except Exception as e:
            log.error(f"Error durante el recorte: {e}")
            sys.exit(1)

    # === Mensaje final ===
    print("\n=== PROCESO COMPLETADO ===")
    print("Los retratos finales están en: Retratos/01_RECORTE_FINAL/")


if __name__ == "__main__":
    main()
