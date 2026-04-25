#!/usr/bin/env python3
"""
main.py — Punto de entrada unificado para Portraits-AI.

Uso:
    python main.py              # Pipeline completo (download + process)
    python main.py --download # Solo descargar
    python main.py --process # Solo procesar imágenes
    python main.py --count   # Contar imágenes
    python main.py -d Mogol # Solo dinastía específica
"""

import argparse
import logging
import sys
from pathlib import Path

BASE_PATH = Path(__file__).parent
sys.path.append(str(BASE_PATH / "python"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Portraits-AI: Sistema de retratos históricos"
    )

    # Flags de fase
    parser.add_argument(
        "--download", "-d", action="store_true", help="Ejecutar fase de descarga"
    )
    parser.add_argument(
        "--process", "-p", action="store_true", help="Ejecutar fase de procesamiento"
    )
    parser.add_argument("--count", "-c", action="store_true", help="Contar imágenes")

    # Opciones
    parser.add_argument("--dynasty", type=str, help="Dinastía específica")
    parser.add_argument("--all", "-a", action="store_true", help="Todas las fases")
    parser.add_argument("--quiet", "-q", action="store_true", help="Reducir output")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log detallado")

    args = parser.parse_args()

    # Default: todas las fases si no se especifica ninguna
    if not (args.download or args.process or args.count):
        args.all = True

    # === CONTEO ===
    if args.count:
        from scraper_core import count_portraits

        stats = count_portraits()
        print("\n=== ESTADO ===")
        print(f"Total: {stats['total_images']}")
        if stats["by_dynasty"]:
            print("\nPor dinastía:")
            for d, c in sorted(stats["by_dynasty"].items()):
                print(f"  {d}: {c}")
        if stats["by_century"]:
            print("\nPor siglo:")
            for s, c in sorted(stats["by_century"].items()):
                print(f"  {s}: {c}")
        return

    # === DESCARGA ===
    if args.all or args.download:
        from scraper_core import load_config, process_dynasty, setup_logging, stats

        if not (BASE_PATH / "monarcas.json").exists():
            log.error("No se encontró monarcas.json")
            sys.exit(1)

        # Setup logging
        log_file = setup_logging(verbose=args.verbose)

        # Stats accumulator
        stats = {
            "dynasties_processed": 0,
            "monarchs_with_images": 0,
            "monarchs_empty": 0,
            "images_downloaded": 0,
            "images_failed": 0,
        }

        config = load_config()

        if args.dynasty:
            if args.dynasty not in config:
                log.error(f"Dinastía '{args.dynasty}' no encontrada")
                log.info(f"Disponibles: {', '.join(config.keys())}")
                sys.exit(1)

            log.info(f"\n=== {args.dynasty} ===")
            process_dynasty(args.dynasty, config[args.dynasty], stats)
            stats["dynasties_processed"] = 1
        else:
            log.info("\n=== FASE: DESCARGA ===")
            for dyn_name, dyn_config in config.items():
                log.info(f"\n>> {dyn_name}")
                process_dynasty(dyn_name, dyn_config, stats)
                stats["dynasties_processed"] += 1

        print("\n=== DESCARGAS ===")
        print(f"Dinastías: {stats['dynasties_processed']}")
        print(f"Con imágenes: {stats['monarchs_with_images']}")
        print(f"Sin imágenes: {stats['monarchs_empty']}")
        print(f"Descargadas: {stats['images_downloaded']}")
        print(f"Fallidas: {stats['images_failed']}")
        print(f"Log: {log_file}")

    # === PROCESAMIENTO ===
    if args.all or args.process:
        from recortar_retratos import procesar_recorte_inteligente

        log.info("\n=== FASE: RECORTE ===")
        try:
            procesar_recorte_inteligente()
        except Exception as e:
            log.error(f"Error durante recorte: {e}")
            sys.exit(1)

    print("\n=== COMPLETADO ===")
    print("Dataset: Retratos/")
    print("Output: Retratos/01_RECORTE_FINAL/")


if __name__ == "__main__":
    main()
