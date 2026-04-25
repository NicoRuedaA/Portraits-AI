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
DINASTIA_NOMBRE = "Rusa"

# Cabeceras para simular un navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Palabras clave para identificar retratos válidos
KEYWORDS = ['portrait', 'painting', 'zar', 'czar', 'emperor', 'empress', 'zarina', 'emperatriz', 'gran duque', 'retrato']
# Palabras clave para intentar excluir archivos de ruido
EXCLUDE_KEYWORDS = ['arms', 'coa', 'map', 'flag', 'svg', 'palace', 'mapa', 'familia']


# Lista de Monarcas Rusos (Nombre para búsqueda, Año inicio, Año fin, Siglo)
MONARCAS_RUSOS = [
    # Gran Ducado de Moscú (Siglos XIV-XVI)
    ("Dmitri Donskói", 1359, 1389, "Siglo XIV"),
    ("Basilio I de Moscú", 1389, 1425, "Siglo XV"),
    ("Basilio II de Moscú", 1425, 1462, "Siglo XV"),
    ("Iván III de Rusia", 1462, 1505, "Siglo XV"),
    ("Basilio III de Rusia", 1505, 1533, "Siglo XVI"),
    
    # Zarato y Imperio Ruso (Siglos XVI-XIX)
    ("Iván IV de Rusia", 1547, 1584, "Siglo XVI"),
    ("Fiódor I de Rusia", 1584, 1598, "Siglo XVI"),
    ("Miguel I de Rusia", 1613, 1645, "Siglo XVII"),
    ("Alejo I de Rusia", 1645, 1676, "Siglo XVII"),
    ("Pedro I de Rusia", 1682, 1725, "Siglo XVII"), 
    ("Catalina I de Rusia", 1725, 1727, "Siglo XVIII"),
    ("Isabel I de Rusia", 1741, 1762, "Siglo XVIII"),
    ("Catalina II de Rusia", 1762, 1796, "Siglo XVIII"),
    ("Alejandro I de Rusia", 1801, 1825, "Siglo XIX"),
]

# ----------------------------------------------------------------------
# 2. Función Principal de Descarga
# ----------------------------------------------------------------------

def descargar_retratos_multiples(monarca):
    nombre_busqueda, inicio, fin, siglo = monarca
    
    # 1. Rutas
    carpeta_siglo = os.path.join(BASE_DIR, siglo)
    carpeta_dinastia = os.path.join(carpeta_siglo, DINASTIA_NOMBRE)
    
    # Carpeta final: .../Siglo/Dinastía/Nombre Monarca/
    carpeta_monarca = os.path.join(carpeta_dinastia, nombre_busqueda)
    
    os.makedirs(carpeta_monarca, exist_ok=True)
    
    print(f"\n--- Procesando: {nombre_busqueda} ({DINASTIA_NOMBRE}/{siglo}) ---")

    try:
        # 2. Buscar la página en Wikipedia
        wikipedia.set_lang("es")
        pagina = wikipedia.page(nombre_busqueda, auto_suggest=False, redirect=True)
        
        if not pagina.images:
            print(f"   ERROR: No se encontraron imágenes para '{nombre_busqueda}'.")
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
            print(f"   ADVERTENCIA: No se encontraron imágenes válidas para '{nombre_busqueda}' después del filtrado.")
            return

        print(f"   Encontrados {len(urls_validas)} retratos válidos.")

        # 4. Descargar y guardar cada URL
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
    print("--- Iniciando descarga MÚLTIPLE de retratos rusos (Moscovia incluida) ---")
    for monarca in MONARCAS_RUSOS:
        descargar_retratos_multiples(monarca)
    print("\n--- Proceso de descarga masiva completado ---")