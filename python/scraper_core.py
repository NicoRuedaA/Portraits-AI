import os
import requests
import wikipedia
import time
import logging
import json

# --- CONFIGURACIÓN GLOBAL ---
BASE_DIR = os.path.join(os.getcwd(), "Retratos")
HEADERS = {
    "User-Agent": "PortraitsAI-Bot/1.0 (https://github.com/yourusername/Portraits-AI; your@email.com) requests/2.31.0"
}
KEYWORDS = [
    "portrait",
    "painting",
    "king",
    "queen",
    "rey",
    "reina",
    "retrato",
    "roi",
    "monarque",
    "emperor",
    "tsar",
    "sultan",
]
EXCLUDE_KEYWORDS = [
    "arms",
    "coa",
    "map",
    "flag",
    "svg",
    "castle",
    "mapa",
    "familia",
    "château",
    "blason",
    "shield",
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def setup_wikipedia(lang="es"):
    wikipedia.set_lang(lang)


def get_valid_images(page_title):
    """Busca imágenes válidas en una página de Wikipedia filtrando por palabras clave."""
    try:
        page = wikipedia.page(page_title, auto_suggest=False)
        images = page.images
        valid_urls = []

        for img_url in images:
            img_name = img_url.lower()
            # Filtro: Debe tener una keyword positiva y NO tener ninguna negativa
            if any(k in img_name for k in KEYWORDS) and not any(
                e in img_name for e in EXCLUDE_KEYWORDS
            ):
                if img_url.endswith((".jpg", ".jpeg", ".png")):
                    valid_urls.append(img_url)
        return valid_urls
    except Exception as e:
        logging.error(f"Error accediendo a Wikipedia para {page_title}: {e}")
        return []


def descargar_imagen(url, ruta_destino):
    """Descarga una imagen desde una URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            with open(ruta_destino, "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        logging.error(f"Error descargando {url}: {e}")
    return False


def procesar_monarcas(lista_monarcas, dinastia_nombre, lang="es"):
    """Procesa una lista de monarcas: busca y descarga sus retratos."""
    setup_wikipedia(lang)

    for nombre, inicio, fin, siglo in lista_monarcas:
        # Crear estructura de carpetas: Retratos/Siglo/Dinastia/Nombre (Años)
        carpeta_nombre = f"{nombre} {inicio}-{fin}"
        ruta_base = os.path.join(BASE_DIR, siglo, dinastia_nombre, carpeta_nombre)
        os.makedirs(ruta_base, exist_ok=True)

        logging.info(f"Buscando retratos para: {nombre} ({siglo})")
        urls = get_valid_images(nombre)

        count = 1
        for url in urls[:5]:  # Limitar a 5 imágenes por monarca para evitar spam
            extension = url.split(".")[-1]
            nombre_archivo = f"{nombre}_{count}.{extension}"
            ruta_final = os.path.join(ruta_base, nombre_archivo)

            if not os.path.exists(ruta_final):
                if descargar_imagen(url, ruta_final):
                    logging.info(f"  [OK] Guardado: {nombre_archivo}")
                    count += 1
                    time.sleep(1)  # Respetar rate limits
            else:
                logging.info(f"  [SKIP] Ya existe: {nombre_archivo}")
                count += 1


if __name__ == "__main__":
    # Ejemplo de uso con datos franceses (se puede expandir o leer de un JSON)
    FRANCESES = [
        ("Felipe VI de Francia", 1328, 1350, "Siglo XIV"),
        ("Carlos V de Francia", 1364, 1380, "Siglo XIV"),
        ("Carlos VII de Francia", 1422, 1461, "Siglo XV"),
        ("Luis XIV de Francia", 1643, 1715, "Siglo XVII"),
    ]
    procesar_monarcas(FRANCESES, "Francesa")
