import os
import json
import logging
import sys

# Añadir carpetas de scripts al PATH con rutas absolutas
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_PATH, "python"))
sys.path.append(os.path.join(BASE_PATH, "Retratos", "Python"))

try:
    from scraper_core import procesar_monarcas
except ImportError:
    logging.error(
        "No se pudo cargar scraper_core. Asegúrate de que existe en la carpeta python/"
    )
    procesar_monarcas = None

try:
    from recortar_retratos import procesar_recorte_inteligente
except ImportError:
    logging.error(
        "No se pudo cargar recortar_retratos. Asegúrate de que existe en Retratos/Python/"
    )
    procesar_recorte_inteligente = None

# Configuración
CONFIG_FILE = "monarcas.json"
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    print("=== PORTRAITS AI: SISTEMA UNIFICADO ===")

    # 1. Cargar configuración de monarcas
    if not os.path.exists(CONFIG_FILE):
        logging.error(f"No se encontró el archivo {CONFIG_FILE}. Abortando.")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        datos_atlas = json.load(f)

    # 2. Fase de Descarga (Scraping)
    print("\n--- FASE 1: DESCARGA DE RETRATOS ---")
    if procesar_monarcas:
        for dinastia, info in datos_atlas.items():
            print(f"\n>> Procesando Dinastía: {dinastia}")
            procesar_monarcas(info["monarcas"], dinastia, lang=info.get("lang", "es"))
    else:
        print("Saltando descarga: scraper_core no disponible.")

    # 3. Fase de Procesamiento (Recorte y Mejora Visual)
    print("\n--- FASE 2: RECORTE Y MEJORA VISUAL ---")
    if procesar_recorte_inteligente:
        try:
            procesar_recorte_inteligente()
        except Exception as e:
            logging.error(f"Error durante el recorte: {e}")
    else:
        print("Saltando recorte: recortar_retratos no disponible.")

    print("\n=== PROCESO COMPLETADO CON ÉXITO ===")
    print("Los retratos finales están en: 01_RECORTE_FINAL/")


if __name__ == "__main__":
    main()
