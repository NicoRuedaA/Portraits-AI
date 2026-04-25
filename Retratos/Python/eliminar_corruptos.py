import os
import cv2
import shutil

# --- CONFIGURACIÓN ---
# Directorio raíz del dataset (donde se encuentran Siglo XIV, Siglo XV, etc.)
BASE_DIR = os.getcwd() 
# Carpeta donde se moverán las imágenes que no pasan el filtro.
CARPETA_DESCARTADOS = os.path.join(BASE_DIR, "00_DESCARTADOS")

# Archivo de entrenamiento para detección facial (OpenCV default)
# El archivo .xml debe existir en tu sistema para que funcione.
# Lo mejor es descargarlo de los repositorios de OpenCV (ej: 'haarcascade_frontalface_default.xml')
# Si el script falla en encontrarlo, necesitarás la ruta completa.
try:
    # Intenta usar la ruta estándar si OpenCV está instalado correctamente
    haar_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    if not os.path.exists(haar_cascade_path):
        print("ADVERTENCIA: El archivo haarcascade_frontalface_default.xml no se encontró en la ruta estándar de OpenCV.")
        print("Por favor, descarga este archivo y colócalo en el directorio raíz o ajusta la ruta.")
        # Usaremos la ruta directamente si no lo encontramos
        raise FileNotFoundError 
except FileNotFoundError:
    # Opción alternativa si no está en la ruta estándar (puedes ajustar esta ruta)
    haar_cascade_path = 'haarcascade_frontalface_default.xml' 
    
# Cargar el clasificador
face_cascade = cv2.CascadeClassifier(haar_cascade_path)

def mover_a_descartados(ruta_archivo, razon):
    """Mueve el archivo a la carpeta de descartados, manteniendo su estructura."""
    
    # 1. Crear la carpeta de descartados si no existe
    os.makedirs(CARPETA_DESCARTADOS, exist_ok=True)
    
    # 2. Crear una subcarpeta basada en la razón del descarte
    carpeta_razon = os.path.join(CARPETA_DESCARTADOS, razon)
    os.makedirs(carpeta_razon, exist_ok=True)

    # 3. Mover el archivo
    nombre_archivo = os.path.basename(ruta_archivo)
    ruta_destino = os.path.join(carpeta_razon, nombre_archivo)
    
    # Usamos shutil.move para mover, no para copiar
    try:
        shutil.move(ruta_archivo, ruta_destino)
        print(f"   [DESCARTADO - {razon}] -> Movido a: {ruta_destino}")
        return True
    except Exception as e:
        print(f"   ERROR al mover {nombre_archivo}: {e}")
        return False


def filtrar_imagenes_sin_rostro(directorio_raiz):
    """Recorre recursivamente y mueve las imágenes sin rostro detectado."""
    
    total_revisado = 0
    total_descartado = 0
    CARPETA_EXCLUIR = ['venv', '00_DESCARTADOS']

    print(f"Iniciando filtrado por detección facial en: {directorio_raiz}\n")

    for raiz, subdirs, archivos in os.walk(directorio_raiz):
        
        # Excluir carpetas como 'venv' y '00_DESCARTADOS' de la recursión
        subdirs[:] = [d for d in subdirs if d not in CARPETA_EXCLUIR]
        
        if raiz == directorio_raiz:
            continue
            
        print(f"Revisando carpeta: {os.path.basename(raiz)}")

        for archivo in archivos:
            if archivo.lower().endswith(('.jpg', '.jpeg', '.png')):
                total_revisado += 1
                ruta_completa = os.path.join(raiz, archivo)
                
                try:
                    # Cargar la imagen
                    img = cv2.imread(ruta_completa)
                    
                    if img is None:
                        # Si OpenCV no puede leer la imagen (archivo corrupto o vacío)
                        if mover_a_descartados(ruta_completa, "CORRUPTO"):
                            total_descartado += 1
                        continue

                    # Convertir a escala de grises para mejorar la detección (es más rápido)
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                    # Detectar rostros
                    # scaleFactor y minNeighbors pueden ser ajustados para sensibilidad
                    rostros = face_cascade.detectMultiScale(
                        gray, 
                        scaleFactor=1.1, 
                        minNeighbors=5, 
                        minSize=(50, 50) # Tamaño mínimo del rostro en píxeles (50x50 es buen inicio)
                    )

                    if len(rostros) == 0:
                        # ¡Cero rostros detectados! Descartar.
                        if mover_a_descartados(ruta_completa, "SIN_ROSTRO"):
                            total_descartado += 1
                    
                    # Opcional: Si quieres mover las imágenes con MÚLTIPLES rostros (escenas)
                    # if len(rostros) > 2:
                    #     if mover_a_descartados(ruta_completa, "MULTIPLES_ROSTROS"):
                    #         total_descartado += 1

                except Exception as e:
                    print(f"   ERROR de procesamiento en {archivo}: {e}")
                    if mover_a_descartados(ruta_completa, "ERROR_PROCESO"):
                        total_descartado += 1
                        
    print("\n-------------------------------------------")
    print(f"✅ Filtrado completado.")
    print(f"Imágenes revisadas: {total_revisado}")
    print(f"Imágenes movidas a '00_DESCARTADOS': {total_descartado}")
    print("-------------------------------------------")
    
# ----------------------------------------------------------------------
# Ejecución principal
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # ¡ADVERTENCIA! Ejecutar este script desde una terminal con privilegios de Administrador 
    # es altamente recomendable para evitar errores de acceso denegado (WinError 5).
    
    # Intenta descargar el clasificador si falta (solo si lo pusiste en la ruta del script)
    if not os.path.exists('haarcascade_frontalface_default.xml') and not os.path.exists(haar_cascade_path):
        print("Por favor, descarga el archivo XML necesario (haarcascade_frontalface_default.xml) para la detección facial.")
    else:
        filtrar_imagenes_sin_rostro(BASE_DIR)