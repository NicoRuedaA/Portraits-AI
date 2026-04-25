import os
import requests
import wikipedia
import time

# --- CONFIGURACIÓN GENERAL ---
BASE_DIR = os.getcwd() 
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Palabras clave para filtrado
KEYWORDS = ['portrait', 'painting', 'king', 'queen', 'shah', 'sultan', 'shogun', 'emperor', 'retrato', 'emperador', 'negus']
EXCLUDE_KEYWORDS = ['arms', 'coa', 'map', 'flag', 'svg', 'castle', 'mapa', 'familia', 'tomb', 'architecture']

# --- LISTAS DE MONARCAS (5 elementos: Nombre, Dinastía Carpeta, Año Inicio, Año Fin, Siglo) ---

MONARCAS = [
    # 1. MOGOLES (INDIA)
    ("Babur", "Mogol", 1526, 1530, "Siglo XVI"),
    ("Humayun", "Mogol", 1530, 1556, "Siglo XVI"),
    ("Akbar", "Mogol", 1556, 1605, "Siglo XVI"),
    ("Jahangir", "Mogol", 1605, 1627, "Siglo XVII"),
    ("Shah Jahan", "Mogol", 1628, 1658, "Siglo XVII"),
    ("Aurangzeb", "Mogol", 1658, 1707, "Siglo XVII"),
    ("Bahadur Shah I", "Mogol", 1707, 1712, "Siglo XVIII"),
    ("Shah Alam II", "Mogol", 1759, 1806, "Siglo XVIII"),
    ("Bahadur Shah II", "Mogol", 1837, 1857, "Siglo XIX"),

    # 2. JAPONESES (Tokugawa/Emperadores)
    ("Tokugawa Ieyasu", "Japonesa", 1603, 1605, "Siglo XVII"),
    ("Tokugawa Hidetada", "Japonesa", 1605, 1623, "Siglo XVII"),
    ("Tokugawa Iemitsu", "Japonesa", 1623, 1651, "Siglo XVII"),
    ("Tokugawa Tsunayoshi", "Japonesa", 1680, 1709, "Siglo XVII"),
    ("Tokugawa Yoshimune", "Japonesa", 1716, 1745, "Siglo XVIII"),
    ("Tokugawa Ieharu", "Japonesa", 1760, 1786, "Siglo XVIII"),
    ("Emperador Kōkaku", "Japonesa", 1780, 1817, "Siglo XVIII"),
    ("Emperador Ninkō", "Japonesa", 1817, 1846, "Siglo XIX"),
    
    # 3. ETIOPE (NOMBRES DE BÚSQUEDA SIMPLIFICADOS PARA EVITAR PAGE ERROR)
    ("Dawit I", "Etiopía", 1382, 1413, "Siglo XIV"), # Antes: "Dawit I de Etiopía"
    ("Yeshaq I", "Etiopía", 1414, 1429, "Siglo XV"),
    ("Zara Yaqob", "Etiopía", 1434, 1468, "Siglo XV"),
    ("Lebna Dengel", "Etiopía", 1508, 1540, "Siglo XVI"),
    ("Gelawdewos", "Etiopía", 1540, 1559, "Siglo XVI"),
    ("Iyoas II", "Etiopía", 1818, 1821, "Siglo XIX"),
]

# ----------------------------------------------------------------------
# A. FUNCIÓN DE DESCARGA
# ----------------------------------------------------------------------

def descargar_retratos_multiples(monarca):
    # Ya se espera una tupla de 5 elementos
    nombre_busqueda, dinastia_nombre, inicio, fin, siglo = monarca
    
    # 1. Rutas
    carpeta_siglo = os.path.join(BASE_DIR, siglo)
    carpeta_dinastia = os.path.join(carpeta_siglo, dinastia_nombre)
    carpeta_monarca = os.path.join(carpeta_dinastia, nombre_busqueda)
    
    print(f"\n--- Procesando: {nombre_busqueda} ({dinastia_nombre}/{siglo}) ---")

    try:
        pagina = None
        
        # 2. Intentar buscar primero en Español
        try:
            wikipedia.set_lang("es")
            pagina = wikipedia.page(nombre_busqueda, auto_suggest=False, redirect=True)
        except wikipedia.exceptions.PageError:
            # Si falla en español, intentar en Inglés (más documentado para estos casos)
            print(f"   ADVERTENCIA: Búsqueda en español fallida. Intentando en inglés para '{nombre_busqueda}'.")
            wikipedia.set_lang("en")
            pagina = wikipedia.page(nombre_busqueda, auto_suggest=False, redirect=True)

        if not pagina.images:
            print(f"   ADVERTENCIA: No se encontraron imágenes en la página de Wikipedia para '{nombre_busqueda}'.")
            return

        # 3. Filtrar las URLs
        urls_validas = []
        for url in pagina.images:
            url_min = url.lower()
            is_valid_format = url_min.endswith(('.jpg', '.jpeg', '.png'))
            contains_keyword = any(keyword in url_min for keyword in KEYWORDS)
            is_not_excluded = not any(keyword in url_min for keyword in EXCLUDE_KEYWORDS)
            
            if is_valid_format and contains_keyword and is_not_excluded:
                urls_validas.append(url)

        if not urls_validas:
            print(f"   ADVERTENCIA: No se encontraron imágenes válidas para '{nombre_busqueda}' después del filtrado. Saltando creación de carpeta.")
            return
        
        # 4. CREACIÓN CONDICIONAL DE CARPETAS
        os.makedirs(carpeta_monarca, exist_ok=True)
        print(f"   Encontrados {len(urls_validas)} retratos válidos. Creando carpeta.")

        # 5. Descargar y guardar cada URL
        for i, final_url in enumerate(urls_validas):
            nombre_archivo = f"{nombre_busqueda} {inicio}-{fin}_{i+1}.jpg"
            ruta_final = os.path.join(carpeta_monarca, nombre_archivo) 
            
            print(f"   Descargando {i+1}/{len(urls_validas)}: {nombre_archivo}")

            try:
                time.sleep(1) 
                contenido_imagen = requests.get(final_url, headers=HEADERS, stream=True, timeout=15).content
                
                with open(ruta_final, 'wb') as f:
                    f.write(contenido_imagen)
                
            except requests.exceptions.RequestException as e:
                print(f"   ERROR en la descarga de {nombre_archivo}. {e}")
            except Exception as e:
                print(f"   ERROR INESPERADO al guardar el archivo: {e}")

        print(f"   ÉXITO: Procesamiento de {nombre_busqueda} completado.")

    except wikipedia.exceptions.PageError:
        print(f"   ERROR FATAL: No se encontró la página de Wikipedia (ni en español ni en inglés) para '{nombre_busqueda}'.")
    except Exception as e:
        print(f"   ERROR INESPERADO (del script principal): {e}")


def ejecutar_descarga():
    """Ejecuta la descarga de todos los monarcas definidos en la lista MONARCAS."""
    print("--- Iniciando DESCARGA MASIVA de retratos de Asia y África ---")
    for monarca in MONARCAS:
        descargar_retratos_multiples(monarca)
    print("\n--- Proceso de DESCARGA completado ---")


# ----------------------------------------------------------------------
# B. FUNCIÓN DE CONTEO
# ----------------------------------------------------------------------

def contar_archivos_de_imagen(directorio_raiz):
    # ... (El código de conteo es el mismo y no tiene errores de desempacado)
    contador_archivos = 0
    EXTENSIONES_VALIDAS = ('.jpg', '.jpeg', '.png')
    CARPETAS_A_EXCLUIR = ['venv', '__pycache__', '.git'] 
    
    print(f"Iniciando conteo de retratos válidos en: {directorio_raiz}\n")

    for raiz, subdirs, archivos in os.walk(directorio_raiz):
        
        subdirs[:] = [d for d in subdirs if d.lower() not in CARPETAS_A_EXCLUIR]
        
        if raiz == directorio_raiz:
            print(f"Se ignoran {len(archivos)} archivos en el directorio raíz.")
            continue
        
        num_archivos_contados = 0
        for archivo in archivos:
            if archivo.lower().endswith(EXTENSIONES_VALIDAS):
                num_archivos_contados += 1

        contador_archivos += num_archivos_contados
        
        if num_archivos_contados > 0:
            print(f"   [+] Carpeta '{os.path.basename(raiz)}': {num_archivos_contados} retratos")

    return contador_archivos

def ejecutar_conteo():
    """Ejecuta el conteo de archivos en el directorio actual."""
    directorio_actual = os.getcwd()
    total = contar_archivos_de_imagen(directorio_actual)
    
    print("\n-------------------------------------------")
    print(f"✅ ¡Conteo finalizado!")
    print(f"TOTAL DE RETRATOS LISTOS PARA LORA: {total}")
    print("-------------------------------------------")


# ----------------------------------------------------------------------
# C. INTERFAZ DE USUARIO
# ----------------------------------------------------------------------

if __name__ == "__main__":
    
    print("--- GESTIÓN DE DATASET ASIA Y ÁFRICA PARA MOD CK3 ---")
    print("Por favor, selecciona una opción:")
    print("1. Ejecutar DESCARGA MASIVA (Mogol, Japonés, Etíope).")
    print("2. Ejecutar CONTEO de archivos de retratos válidos.")
    
    opcion = input("Introduce 1 o 2: ")
    
    if opcion == '1':
        ejecutar_descarga()
    elif opcion == '2':
        ejecutar_conteo()
    else:
        print("Opción no válida. Por favor, reinicia el script e introduce 1 o 2.")