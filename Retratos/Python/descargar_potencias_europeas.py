import os
import requests
import wikipedia
import time

# ----------------------------------------------------------------------
# 1. Configuración de datos y ruta
# ----------------------------------------------------------------------

# Directorio base: ¡Asegúrate de que esta ruta sea correcta en tu PC!
BASE_DIR = r"C:\Users\alumne-DAM\Documents\DAM\Retratos"

# Cabeceras para simular un navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Palabras clave para identificar retratos válidos
KEYWORDS = ['portrait', 'painting', 'king', 'queen', 'rey', 'reina', 'retrato', 'monarch']
# Palabras clave para intentar excluir archivos de ruido
EXCLUDE_KEYWORDS = ['arms', 'coa', 'map', 'flag', 'svg', 'castle', 'mapa', 'familia', 'palace']


# --- DATOS ESPAÑOLES ---
MONARCAS_ESPANOL = [
    ("Enrique II de Castilla", "Española", 1369, 1379, "Siglo XIV"),
    ("Juan I de Castilla", "Española", 1379, 1390, "Siglo XIV"),
    ("Enrique III de Castilla", "Española", 1390, 1406, "Siglo XV"),
    ("Juan II de Castilla", "Española", 1406, 1454, "Siglo XV"),
    ("Isabel I de Castilla", "Española", 1474, 1504, "Siglo XV"),
    ("Carlos I de España", "Española", 1516, 1556, "Siglo XVI"),
    ("Felipe II de España", "Española", 1556, 1598, "Siglo XVI"),
    ("Felipe IV de España", "Española", 1621, 1665, "Siglo XVII"),
    ("Felipe V de España", "Española", 1700, 1746, "Siglo XVIII"),
    ("Carlos III de España", "Española", 1759, 1788, "Siglo XVIII"),
    ("Fernando VII de España", "Española", 1813, 1833, "Siglo XIX"),
]

# --- DATOS BRITÁNICOS ---
MONARCAS_BRITANICOS = [
    ("Eduardo III de Inglaterra", "Británica", 1327, 1377, "Siglo XIV"),
    ("Ricardo II de Inglaterra", "Británica", 1377, 1399, "Siglo XIV"),
    ("Enrique V de Inglaterra", "Británica", 1413, 1422, "Siglo XV"),
    ("Enrique VII de Inglaterra", "Británica", 1485, 1509, "Siglo XV"),
    ("Enrique VIII de Inglaterra", "Británica", 1509, 1547, "Siglo XVI"),
    ("Isabel I de Inglaterra", "Británica", 1558, 1603, "Siglo XVI"),
    ("Jacobo I de Inglaterra", "Británica", 1603, 1625, "Siglo XVII"),
    ("Carlos I de Inglaterra", "Británica", 1625, 1649, "Siglo XVII"),
    ("Carlos II de Inglaterra", "Británica", 1660, 1685, "Siglo XVII"),
    ("Ana de Gran Bretaña", "Británica", 1702, 1714, "Siglo XVIII"),
    ("Jorge III del Reino Unido", "Británica", 1760, 1820, "Siglo XVIII"),
    ("Jorge IV del Reino Unido", "Británica", 1820, 1830, "Siglo XIX"),
]

# ----------------------------------------------------------------------
# 2. Función Principal de Descarga (Aplica Creación Condicional de Carpeta)
# ----------------------------------------------------------------------

def descargar_retratos_multiples(monarca):
    nombre_busqueda, dinastia_nombre, inicio, fin, siglo = monarca
    
    # 1. Rutas (no creamos las carpetas aún)
    carpeta_siglo = os.path.join(BASE_DIR, siglo)
    carpeta_dinastia = os.path.join(carpeta_siglo, dinastia_nombre)
    carpeta_monarca = os.path.join(carpeta_dinastia, nombre_busqueda)
    
    print(f"\n--- Procesando: {nombre_busqueda} ({dinastia_nombre}/{siglo}) ---")

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
            
            # Criterio de filtrado (Formato, Palabra clave, Exclusión)
            is_valid_format = url_min.endswith(('.jpg', '.jpeg', '.png'))
            contains_keyword = any(keyword in url_min for keyword in KEYWORDS)
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
    print("--- Iniciando descarga MÚLTIPLE de retratos españoles y británicos ---")
    
    # Procesar monarcas españoles
    for monarca in MONARCAS_ESPANOL:
        descargar_retratos_multiples(monarca)

    # Procesar monarcas británicos
    for monarca in MONARCAS_BRITANICOS:
        descargar_retratos_multiples(monarca)
        
    print("\n--- Proceso de descarga masiva completado ---")