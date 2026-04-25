import os
import cv2
from PIL import Image

# --- CONFIGURACIÓN ---
BASE_DIR = os.getcwd()
# Dimensiones finales del retrato (proporción estándar de CK3)
ANCHO_FINAL = 512
ALTO_FINAL = 768
# Factor de zoom vertical (para incluir más torso y menos frente/barbilla)
FACTOR_ZOOM = 0.5
# Ruta al clasificador de rostros
HAARCASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
# Carpeta donde guardar los archivos finales, manteniendo la estructura
CARPETA_SALIDA = os.path.join(BASE_DIR, "01_RECORTE_FINAL")

# Cargar el clasificador
face_cascade = cv2.CascadeClassifier(HAARCASCADE_PATH)


def aplicar_mejoras(img_pil):
    """Aplica mejoras visuales básicas: brillo, contraste y nitidez."""
    from PIL import ImageEnhance

    # 1. Brillo (un poco más luminoso)
    enhancer = ImageEnhance.Brightness(img_pil)
    img_pil = enhancer.enhance(1.05)

    # 2. Contraste (un poco más definido)
    enhancer = ImageEnhance.Contrast(img_pil)
    img_pil = enhancer.enhance(1.1)

    # 3. Nitidez (suave para óleos)
    enhancer = ImageEnhance.Sharpness(img_pil)
    img_pil = enhancer.enhance(1.2)

    return img_pil


def procesar_recorte_inteligente():
    """Recorre recursivamente las imágenes, detecta el rostro, recorta y guarda."""

    total_procesado = 0
    total_fallido = 0
    # Modificación: Solo excluimos carpetas de sistema (venv) y la carpeta de salida.
    CARPETA_EXCLUIR_RECURSION = ["venv", "01_RECORTE_FINAL", "00_DESCARTADOS"]

    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    print(f"Iniciando recorte inteligente mejorado a {ANCHO_FINAL}x{ALTO_FINAL}...\n")

    for raiz, subdirs, archivos in os.walk(BASE_DIR):
        # Excluir carpetas de trabajo y el entorno virtual
        subdirs[:] = [d for d in subdirs if d not in CARPETA_EXCLUIR_RECURSION]

        # Saltamos el directorio raíz
        if raiz == BASE_DIR:
            continue

        # El script ahora procesará las subcarpetas de 00_DESCARTADOS si existen.
        if "00_DESCARTADOS" in raiz:
            print(
                f"--- Incluyendo imágenes de la carpeta: {os.path.basename(raiz)} ---"
            )

        for archivo in archivos:
            if archivo.lower().endswith((".jpg", ".jpeg", ".png")):
                total_procesado += 1
                ruta_completa = os.path.join(raiz, archivo)

                # Crear la ruta de salida, manteniendo la estructura
                # Esto es importante: mueve la estructura de Siglo/Dinastía/Monarca dentro de 01_RECORTE_FINAL
                # La estructura de las carpetas 00_DESCARTADOS se mantendrá dentro de 01_RECORTE_FINAL también.
                ruta_salida_carpeta = raiz.replace(BASE_DIR, CARPETA_SALIDA, 1)
                os.makedirs(ruta_salida_carpeta, exist_ok=True)
                ruta_salida_completa = os.path.join(ruta_salida_carpeta, archivo)

                try:
                    # 1. Detección Facial
                    img = cv2.imread(ruta_completa)
                    if img is None:
                        raise ValueError("Imagen no pudo ser cargada por OpenCV.")

                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    rostros = face_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
                    )

                    if len(rostros) == 0:
                        # Si no se detecta el rostro (e.g., retrato de perfil, muy estilizado),
                        # usamos el centro de la imagen como fallback para un recorte ciego.
                        x_centro = img.shape[1] // 2
                        y_centro = img.shape[0] // 2
                    else:
                        # Usar el rostro más grande (el primero detectado)
                        (x, y, w, h) = rostros[0]
                        x_centro = x + w // 2
                        y_centro = y + int(h * FACTOR_ZOOM)

                    # 2. Definir la "Caja de Enfoque"
                    ratio = ANCHO_FINAL / ALTO_FINAL
                    crop_h = img.shape[0]
                    crop_w = int(crop_h * ratio)

                    if crop_w > img.shape[1]:
                        crop_w = img.shape[1]
                        crop_h = int(crop_w / ratio)

                    # 3. Calcular el punto inicial del recorte
                    x1 = max(0, x_centro - crop_w // 2)
                    y1 = max(0, y_centro - crop_h // 2)

                    x1 = min(x1, img.shape[1] - crop_w)
                    y1 = min(y1, img.shape[0] - crop_h)

                    # 4. Aplicar Recorte y Redimensionamiento con PIL
                    Image.MAX_IMAGE_PIXELS = None  # Permitir imágenes muy grandes
                    img_pil = Image.open(ruta_completa)

                    # Convertir a RGB si tiene transparencia (evita error RGBA -> JPEG)
                    if img_pil.mode in ("RGBA", "P"):
                        img_pil = img_pil.convert("RGB")

                    img_recortada = img_pil.crop((x1, y1, x1 + crop_w, y1 + crop_h))
                    img_final = img_recortada.resize(
                        (ANCHO_FINAL, ALTO_FINAL), Image.Resampling.LANCZOS
                    )

                    # --- NUEVO: Mejoras Visuales ---
                    img_final = aplicar_mejoras(img_final)

                    # 5. Guardar el resultado

                    img_final.save(ruta_salida_completa, "JPEG")
                    print(
                        f"   [ÉXITO] Recortado y guardado: {os.path.basename(ruta_salida_completa)}"
                    )

                except Exception as e:
                    print(
                        f"   [FALLO] Error procesando {os.path.basename(ruta_completa)}: {e}"
                    )
                    total_fallido += 1

    print("\n-------------------------------------------")
    print("✅ Recorte masivo completado.")
    print(f"Total procesado: {total_procesado}. Fallidos: {total_fallido}")
    print(f"Archivos guardados en la carpeta: {os.path.basename(CARPETA_SALIDA)}")
    print("-------------------------------------------")


# ----------------------------------------------------------------------
# Ejecución principal
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Asegúrate de haber instalado 'Pillow' (pip install Pillow)
    procesar_recorte_inteligente()
