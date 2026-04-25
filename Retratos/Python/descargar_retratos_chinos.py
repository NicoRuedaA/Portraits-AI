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
KEYWORDS = ['portrait', 'painting', 'emperor', 'imperial', 'retrato', 'emperador']
# Palabras clave para intentar excluir archivos de ruido
EXCLUDE_KEYWORDS = ['arms', 'coa', 'map', 'flag', 'svg', 'palace', 'tomb']


# Lista de Monarcas Chinos (Nombre para búsqueda, Dinastía, Año inicio, Año fin, Siglo)
MONARCAS_CHINOS = [
    # Dinastía Ming
    ("Emperador Hongwu", "Ming", 1368, 1398, "Siglo XIV"),
    ("Emperador Yongle", "Ming", 1402, 1424, "Siglo XV"),
    ("Emperador Xuande", "Ming", 1425, 1435, "Siglo XV"),
    ("Emperador Chenghua", "Ming", 1464, 1487, "Siglo XV"),
    ("Emperador Hongzhi", "Ming", 1487, 1505, "Siglo XV"),
    ("Emperador Jiajing", "Ming", 1521, 1567, "Siglo XVI"),
    ("Emperador Wanli", "Ming", 1572, 1620, "Siglo XVI"),
    ("Emperador Chongzhen", "Ming", 1627, 1644, "Siglo XVII"),
    
    # Dinastía Qing
    ("Emperador Shunzhi", "Qing", 1644, 1661, "Siglo XVII"),
    ("Emperador Kangxi", "Qing", 1661, 1722, "Siglo XVII"),
    ("Emperador Yongzheng", "Qing", 1723, 1735, "Siglo XVIII"),
    ("Emperador Qianlong", "Qing", 1735, 1796, "Siglo XVIII"),
    ("Emperador Jiaqing", "Qing", 1796, 1820, "Siglo XVIII"),
    ("Emperador Daoguang", "Qing", 1820, 1850, "Siglo XIX"), 
]

# ----------------------------------------------------------------------
# 2. Función Principal de Descarga
# ----------------------------------------------------------------------

def descargar_retratos_multiples(monarca):
    nombre_busqueda, dinastia, inicio, fin, siglo = monarca
    
    # 1. Rutas (Nombre de la carpeta Monarca se basa en el nombre de búsqueda)
    carpeta_siglo = os.path.join(BASE_DIR, siglo)
    carpeta_dinastia_nombre = os.path.join(carpeta_siglo, dinastia)
    
    # Carpeta final: .../Siglo/Dinastía/Nombre Monarca/
    carpeta_monarca = os.path.join(carpeta_dinastia_nombre, nombre_busqueda)
    
    os.makedirs(carpeta_monarca, exist_ok=True)
    
    print(f"\n--- Procesando: {nombre_busqueda} ({dinastia}/{siglo}) ---")

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
    print("--- Iniciando descarga MÚLTIPLE de retratos chinos ---")
    for monarca in MONARCAS_CHINOS:
        descargar_retratos_multiples(monarca)
    print("\n--- Proceso de descarga masiva completado ---")