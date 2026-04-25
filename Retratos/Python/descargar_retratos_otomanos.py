import os
import requests
import wikipedia
import time

# ----------------------------------------------------------------------
# 1. Configuración de datos y ruta
# ----------------------------------------------------------------------

# Directorio base: ¡Asegúrate de que esta ruta sea correcta en tu PC!
BASE_DIR = r"C:\Users\alumne-DAM\Documents\DAM\Retratos"

# La dinastía
DINASTIA = "Otomana"

# Cabeceras para simular un navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Palabras clave para identificar retratos válidos
KEYWORDS = ['portrait', 'painting', 'sultan', 'image', 'ritratto', 'sultani']
# Palabras clave para intentar excluir archivos de ruido
EXCLUDE_KEYWORDS = ['arms', 'coa', 'map', 'flag', 'family', 'pedigree', 'svg']


# Lista de Monarcas (Nombre, Año de inicio, Año de fin, Siglo)
MONARCAS_OTOMANOS = [
    # Siglo XIV
    ("Orhan I", 1324, 1362, "Siglo XIV"),
    ("Murad I", 1362, 1389, "Siglo XIV"),
    ("Bayezid I", 1389, 1402, "Siglo XIV"),
    
    # Siglo XV
    ("Mehmed I", 1413, 1421, "Siglo XV"),
    ("Murad II", 1421, 1451, "Siglo XV"),
    ("Mehmed II", 1451, 1481, "Siglo XV"),
    ("Bayezid II", 1481, 1512, "Siglo XV"),
    
    # Siglo XVI
    ("Selim I", 1512, 1520, "Siglo XVI"),
    ("Solimán I", 1520, 1566, "Siglo XVI"),
    ("Selim II", 1566, 1574, "Siglo XVI"),
    ("Murad III", 1574, 1595, "Siglo XVI"),
    ("Mehmed III", 1595, 1603, "Siglo XVI"),
    
    # Siglo XVII
    ("Ahmed I", 1603, 1617, "Siglo XVII"),
    ("Mustafa I", 1617, 1623, "Siglo XVII"),
    ("Osman II", 1618, 1622, "Siglo XVII"),
    ("Murad IV", 1623, 1640, "Siglo XVII"),
    ("Ibrahim", 1640, 1648, "Siglo XVII"),
    ("Mehmed IV", 1648, 1687, "Siglo XVII"),
    ("Solimán II", 1687, 1691, "Siglo XVII"),
    ("Ahmed II", 1691, 1695, "Siglo XVII"),
    
    # Siglo XVIII
    ("Mustafa II", 1695, 1703, "Siglo XVIII"),
    ("Ahmed III", 1703, 1730, "Siglo XVIII"),
    ("Mahmud I", 1730, 1754, "Siglo XVIII"),
    ("Osman III", 1754, 1757, "Siglo XVIII"),
    ("Mustafa III", 1757, 1774, "Siglo XVIII"),
    ("Abdul Hamid I", 1774, 1789, "Siglo XVIII"),
    ("Selim III", 1789, 1807, "Siglo XVIII"),
    
    # Siglo XIX (hasta 1821)
    ("Mustafa IV", 1807, 1808, "Siglo XIX"),
    ("Mahmud II", 1808, 1839, "Siglo XIX"), 
]

# ----------------------------------------------------------------------
# 2. Función Principal de Descarga
# ----------------------------------------------------------------------

def descargar_retratos_multiples(monarca):
    nombre, inicio, fin, siglo = monarca
    
    # 1. Rutas base
    carpeta_siglo = os.path.join(BASE_DIR, siglo)
    carpeta_dinastia = os.path.join(carpeta_siglo, DINASTIA)
    
    # *** CAMBIO CLAVE AQUÍ: Añadir la carpeta del Monarca ***
    carpeta_monarca = os.path.join(carpeta_dinastia, nombre)
    
    os.makedirs(carpeta_monarca, exist_ok=True)
    
    print(f"\n--- Procesando: {nombre} ({siglo}) ---")

    try:
        # 2. Buscar la página en Wikipedia
        wikipedia.set_lang("es")
        pagina = wikipedia.page(nombre, auto_suggest=False, redirect=True)
        
        if not pagina.images:
            print(f"   ERROR: No se encontraron imágenes para '{nombre}'.")
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
            print(f"   ADVERTENCIA: No se encontraron imágenes válidas para '{nombre}' después del filtrado.")
            return

        print(f"   Encontrados {len(urls_validas)} retratos válidos.")

        # 4. Descargar y guardar cada URL
        for i, final_url in enumerate(urls_validas):
            
            # Nombre de archivo con índice: Nombre Monarca [Año-Año]_[Índice].jpg
            nombre_archivo = f"{nombre} {inicio}-{fin}_{i+1}.jpg"
            # *** CAMBIO CLAVE AQUÍ: Usar la carpeta del Monarca ***
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

        print(f"   ÉXITO: Procesamiento de {nombre} completado.")

    except wikipedia.exceptions.PageError:
        print(f"   ERROR: No se encontró la página de Wikipedia para '{nombre}'.")
    except Exception as e:
        print(f"   ERROR INESPERADO (del script principal): {e}")

# ----------------------------------------------------------------------
# 3. Ejecución principal
# ----------------------------------------------------------------------

if __name__ == "__main__":
    print("--- Iniciando descarga MÚLTIPLE de retratos otomanos ---")
    for monarca in MONARCAS_OTOMANOS:
        descargar_retratos_multiples(monarca)
    print("\n--- Proceso de descarga masiva completado ---")