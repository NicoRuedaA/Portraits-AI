import os
import requests
import wikipedia
import time

# 1. Configuración de datos
NOMBRE_MONARCA = "Orhan I"
DINASTIA = "Otomana"
SIGLO = "Siglo XIV"
A_INICIO = 1324
A_FIN = 1362

# Directorio base
BASE_DIR = r"C:\Users\alumne-DAM\Documents\DAM\Retratos"

# Cabeceras para simular un navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def descargar_retrato_filtrado(nombre, inicio, fin, siglo):
    """Busca específicamente un retrato en la página de Wikipedia y lo descarga."""

    # Rutas y nombre de archivo
    carpeta_siglo = os.path.join(BASE_DIR, siglo)
    carpeta_dinastia = os.path.join(carpeta_siglo, DINASTIA)
    nombre_archivo = f"{nombre} {inicio}-{fin}.jpg" 
    ruta_final = os.path.join(carpeta_dinastia, nombre_archivo)

    os.makedirs(carpeta_dinastia, exist_ok=True)
    
    print(f"\n--- Procesando: {nombre} ---")

    try:
        # 1. Buscar la página en Wikipedia
        wikipedia.set_lang("es")
        pagina = wikipedia.page(nombre, auto_suggest=False, redirect=True)
        
        if not pagina.images:
            print(f"   ERROR: No se encontraron imágenes en la página de Wikipedia para '{nombre}'.")
            return

        # 2. Filtrar la URL de la imagen (Prioridad: Retrato)
        url_retrato = None
        url_fallback = None
        
        for url in pagina.images:
            url_min = url.lower()
            
            # Condición 1: Excluir formatos no deseados y buscar palabras clave de retrato
            if url_min.endswith(('.jpg', '.jpeg', '.png')) and any(keyword in url_min for keyword in ['portrait', 'painting', 'sultan']):
                url_retrato = url
                break
            
            # Condición 2: Guardar la primera imagen válida como fallback
            if url_fallback is None and url_min.endswith(('.jpg', '.jpeg', '.png')):
                url_fallback = url

        # 3. Determinar la URL final
        final_url = url_retrato if url_retrato else url_fallback
        
        if not final_url:
            print(f"   ERROR: No se pudo encontrar una URL de imagen válida (.jpg o .png). La URL inicial fue: {pagina.images[0]}")
            return
            
        print(f"   URL seleccionada: {final_url}")
        
        # 4. Descargar la imagen (usando Headers)
        time.sleep(1) 
        
        contenido_imagen = requests.get(final_url, headers=HEADERS, stream=True, timeout=15).content
        
        # 5. Guardar la imagen
        with open(ruta_final, 'wb') as f:
            f.write(contenido_imagen)
        
        print(f"   ÉXITO: Retrato guardado en {ruta_final}")

    except wikipedia.exceptions.PageError:
        print(f"   ERROR: No se encontró la página de Wikipedia para '{nombre}'.")
    except requests.exceptions.RequestException as e:
        print(f"   ERROR: Fallo al descargar la imagen. {e}")
    except Exception as e:
        print(f"   ERROR INESPERADO: {e}")

# ----------------------------------------------------------------------
# Ejecución
# ----------------------------------------------------------------------

if __name__ == "__main__":
    descargar_retrato_filtrado(NOMBRE_MONARCA, A_INICIO, A_FIN, SIGLO)
    print("\n--- Proceso de prueba completado ---")