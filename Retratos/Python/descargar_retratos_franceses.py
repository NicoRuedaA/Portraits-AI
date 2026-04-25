import os
import requests
import wikipedia
import time

# ----------------------------------------------------------------------
# 1. Configuración de datos y ruta
# ----------------------------------------------------------------------

# Directorio base: ¡Asegúrate de que esta ruta sea correcta en tu PC!
BASE_DIR = r"C:\Users\alumne-DAM\Documents\DAM\Retratos"

# Nombre de la Dinastía
DINASTIA_NOMBRE = "Francesa"

# Cabeceras para simular un navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Palabras clave para identificar retratos válidos
KEYWORDS = ['portrait', 'painting', 'king', 'queen', 'rey', 'reina', 'retrato', 'roi', 'monarque']
# Palabras clave para intentar excluir archivos de ruido
EXCLUDE_KEYWORDS = ['arms', 'coa', 'map', 'flag', 'svg', 'castle', 'mapa', 'familia', 'château']


# Lista de Monarcas Franceses (Nombre para búsqueda, Año inicio, Año fin, Siglo)
MONARCAS_FRANCESES = [
    ("Felipe VI de Francia", 1328, 1350, "Siglo XIV"),
    ("Carlos V de Francia", 1364, 1380, "Siglo XIV"),
    ("Carlos VI de Francia", 1380, 1422, "Siglo XV"),
    ("Carlos VII de Francia", 1422, 1461, "Siglo XV"),
    ("Luis XI de Francia", 1461, 1483, "Siglo XV"),
    ("Carlos VIII de Francia", 1483, 1498, "Siglo XV"),
    ("Luis XII de Francia", 1498, 1515, "Siglo XV"),
    ("Francisco I de Francia", 1515, 1547, "Siglo XVI"),
    ("Enrique II de Francia", 1547, 1559, "Siglo XVI"),
    ("Enrique IV de Francia", 1589, 1610, "Siglo XVI"),
    ("Luis XIII de Francia", 1610, 1643, "Siglo XVII"),
    ("Luis XIV de Francia", 1643, 1715, "Siglo XVII"),
    ("Luis XV de Francia", 1715, 1774, "Siglo XVIII"),
    ("Luis XVI de Francia", 1774, 1792, "Siglo XVIII"),
    ("Luis XVIII de Francia", 1814, 1824, "Siglo XIX"),
]

# ----------------------------------------------------------------------
# 2. Función Principal de Descarga
# ----------------------------------------------------------------------

def descargar_retratos_multiples(monarca):
    nombre_busqueda, inicio, fin, siglo = monarca
    
    # 1. Rutas (no creamos las carpetas aún)
    carpeta_siglo = os.path.join(BASE_DIR, siglo)
    carpeta_dinastia = os.path.join(carpeta_siglo, DINASTIA_NOMBRE)
    carpeta_monarca = os.path.join(carpeta_dinastia, nombre_busqueda)
    
    print(f"\n--- Procesando: {nombre_busqueda} ({DINASTIA_NOMBRE}/{siglo}) ---")

    try:
        # 2. Buscar la página en Wikipedia
        wikipedia.set_lang("es")
        pagina = wikipedia.page(nombre_busqueda, auto_suggest=False, redirect=True)
        
        if not pagina.images:
            print(f"   ADVERTENCIA: No se encontraron imágenes en la página de Wikipedia para '{nombre_busqueda}'.")
            return

        # 3. Filtrar las URLs
        urls_validas = []
        
        for url in pagina.images:
            url_min = url.lower()
            
            # Criterio A: Formato de imagen aceptable
            is_valid_format = url_min.endswith(('.jpg', '.jpeg', '.png'))
            # Criterio B: Contiene palabra clave de retrato
            contains_keyword = any(keyword in url_min for keyword in KEYWORDS)
            # Criterio C: No contiene palabras clave de exclusión
            is_not_excluded = not any(keyword in url_min for keyword in EXCLUDE_KEYWORDS)
            
            if is_valid_format and contains_keyword and is_not_excluded:
                urls_validas.append(url)

        if not urls_validas:
            print(f"   ADVERTENCIA: No se encontraron imágenes válidas para '{nombre_busqueda}' después del filtrado. Saltando creación de carpeta.")
            return
        
        # 4. CREACIÓN CONDICIONAL DE CARPETAS: SOLO SI HAY URLs VÁLIDAS
        os.makedirs(carpeta_monarca, exist_ok=True)
        print(f"   Encontrados {len(urls_validas)} retratos válidos. Creando carpeta.")

        # 5. Descargar y guardar cada URL
        for i, final_url in enumerate(urls_validas):
            
            # Nombre de archivo: Nombre Monarca [Año-Año]_[Índice].jpg
            nombre_archivo = f"{nombre_busqueda} {inicio}-{fin}_{i+1}.jpg"
            ruta_final = os.path.join(carpeta_monarca, nombre_archivo) 
            
            print(f"   Descargando {i+1}/{len(urls_validas)}: {nombre_archivo}")

            try:
                time.sleep(1) # Pausa de seguridad entre descargas

                # Solicitud de descarga con Headers
                contenido_imagen = requests.get(final_url, headers=HEADERS, stream=True, timeout=15).content
                
                # Guardar la imagen
                with open(ruta_final, 'wb') as f:
                    f.write(contenido_imagen)
                
            except requests.exceptions.RequestException as e:
                print(f"   ERROR en la descarga de {nombre_archivo}. {e}")
            except Exception as e:
                print(f"   ERROR INESPERADO al guardar el archivo: {e}")

        print(f"   ÉXITO: Procesamiento de {nombre_busqueda} completado.")

    except wikipedia.exceptions.PageError:
        print(f"   ERROR: No se encontró la página de Wikipedia para '{nombre_busqueda}'.")
    except Exception as e:
        print(f"   ERROR INESPERADO (del script principal): {e}")

# ----------------------------------------------------------------------
# 3. Ejecución principal
# ----------------------------------------------------------------------

if __name__ == "__main__":
    print("--- Iniciando descarga MÚLTIPLE de retratos franceses ---")
    for monarca in MONARCAS_FRANCESES:
        descargar_retratos_multiples(monarca)
    print("\n--- Proceso de descarga masiva completado ---")