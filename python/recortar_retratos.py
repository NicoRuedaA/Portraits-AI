#!/usr/bin/env python3
"""
recortar_retratos.py — Pipeline de procesamiento de imágenes para Portraits-AI.

Detecta rostros, recorta al aspecto correcto (2:3 CK3), aplica mejoras
visuales, y guarda con metadata JSON sidecar.

Uso:
    python recortar_retratos.py                  # Procesar todo
    python recortar_retratos.py --min-size 300   # Filtrar imgs < 300px
    python recortar_retratos.py --no-enhance     # Sin mejoras visuales
    python recortar_retratos.py --output-format both  # JPEG + PNG
"""

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import cv2
from PIL import Image, ImageEnhance

# --- CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parent.parent / "Retratos"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "01_RECORTE_FINAL"

# Dimensiones finales del retrato (proporción CK3: 2:3)
DEFAULT_WIDTH = 512
DEFAULT_HEIGHT = 768

# Factor de zoom vertical (para incluir más torso y menos frente/barbilla)
DEFAULT_ZOOM_FACTOR = 0.5

# Tamaño mínimo de imagen para procesar (en píxeles, ancho o alto)
DEFAULT_MIN_SIZE = 200

# Umbral de desenfoque (varianza del Laplaciano; menor = más borroso)
DEFAULT_BLUR_THRESHOLD = 50.0

# Cascadas Haar disponibles (en orden de preferencia)
HAAR_CASCADES = [
    "haarcascade_frontalface_alt2.xml",
    "haarcascade_frontalface_default.xml",
    "haarcascade_frontalface_alt.xml",
    "haarcascade_frontalface_alt_tree.xml",
]

# Carpetas a excluir del recorrido
EXCLUDE_FOLDERS = {
    "venv",
    "01_RECORTE_FINAL",
    "00_DESCARTADOS",
    "__pycache__",
    "logs",
    "Python",
}

# Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def load_cascades() -> list:
    """
    Carga las cascadas Haar disponibles en orden de preferencia.
    Retorna la primera que se cargue correctamente como principal,
    y las demás como alternativas.
    """
    cascades = []
    for cascade_name in HAAR_CASCADES:
        cascade_path = os.path.join(cv2.data.haarcascades, cascade_name)
        if os.path.exists(cascade_path):
            classifier = cv2.CascadeClassifier(cascade_path)
            if not classifier.empty():
                cascades.append(classifier)
                log.debug(f"Cascada cargada: {cascade_name}")
    if not cascades:
        raise FileNotFoundError(
            f"No se encontró ninguna cascada Haar en {cv2.data.haarcascades}"
        )
    log.info(f"Cascadas Haar cargadas: {len(cascades)}")
    return cascades


def is_image_too_small(img_path: Path, min_size: int) -> bool:
    """
    Verifica si una imagen es demasiado pequeña para procesar.

    Args:
        img_path: Ruta a la imagen
        min_size: Tamaño mínimo en píxeles (ancho o alto)

    Returns:
        True si la imagen es demasiado pequeña
    """
    try:
        with Image.open(img_path) as img:
            w, h = img.size
            return w < min_size or h < min_size
    except Exception:
        return True


def is_image_blurry(img_path: Path, threshold: float) -> bool:
    """
    Detecta si una imagen está borrosa usando la varianza del Laplaciano.

    Una varianza baja indica una imagen borrosa. El umbral típico es 50-100.

    Args:
        img_path: Ruta a la imagen
        threshold: Umbral de varianza (menor = más borroso)

    Returns:
        True si la imagen se considera borrosa
    """
    try:
        img = cv2.imread(str(img_path))
        if img is None:
            return True
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        return variance < threshold
    except Exception:
        return True


def detect_face(img, cascades: list, min_face_size: tuple = (50, 50)):
    """
    Detecta rostros usando múltiples cascadas Haar.
    Prueba cada cascada en orden hasta encontrar un rostro.

    Args:
        img: Imagen OpenCV (BGR)
        cascades: Lista de CascadeClassifier
        min_face_size: Tamaño mínimo del rostro (width, height)

    Returns:
        Tuple (x_centro, y_centro, detection_method) o None si no detecta
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    for i, cascade in enumerate(cascades):
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=min_face_size,
        )

        if len(faces) > 0:
            # Usar el rostro más grande
            # Ordenar por área (w*h) descendente
            faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            x, y, w, h = faces_sorted[0]

            cascade_name = (
                HAAR_CASCADES[i] if i < len(HAAR_CASCADES) else f"cascade_{i}"
            )
            return (x, y, w, h, cascade_name)

    return None


def calcular_crop_box(
    img_shape: tuple,
    face_coords: tuple,
    zoom_factor: float,
    target_width: int,
    target_height: int,
):
    """
    Calcula la caja de recorte alrededor del rostro detectado.

    Args:
        img_shape: (alto, ancho, canales) de la imagen
        face_coords: (x, y, w, h) del rostro detectado, o None
        zoom_factor: Factor de desplazamiento vertical (0=cara, 0.5=mitad)
        target_width: Ancho final del retrato
        target_height: Alto final del retrato

    Returns:
        Tuple (x1, y1, crop_w, crop_h) del recorte
    """
    img_h, img_w = img_shape[:2]
    ratio = target_width / target_height

    if face_coords is not None:
        x, y, w, h = face_coords
        x_centro = x + w // 2
        y_centro = y + int(h * zoom_factor)
        detection = "face"
    else:
        # Fallback: centro de la imagen
        x_centro = img_w // 2
        y_centro = img_h // 2
        detection = "center"

    # Calcular tamaño del crop manteniendo ratio
    crop_h = img_h
    crop_w = int(crop_h * ratio)

    if crop_w > img_w:
        crop_w = img_w
        crop_h = int(crop_w / ratio)

    # Calcular posición inicial
    x1 = max(0, x_centro - crop_w // 2)
    y1 = max(0, y_centro - crop_h // 2)

    # Asegurar que el crop no exceda los bordes
    x1 = min(x1, img_w - crop_w)
    y1 = min(y1, img_h - crop_h)

    return x1, y1, crop_w, crop_h, detection


def aplicar_mejoras(
    img_pil, brightness: float = 1.05, contrast: float = 1.1, sharpness: float = 1.2
):
    """
    Aplica mejoras visuales: brillo, contraste y nitidez.

    Args:
        img_pil: Imagen PIL
        brightness: Factor de brillo (1.0 = sin cambio)
        contrast: Factor de contraste (1.0 = sin cambio)
        sharpness: Factor de nitidez (1.0 = sin cambio)

    Returns:
        Imagen PIL mejorada
    """
    if brightness != 1.0:
        img_pil = ImageEnhance.Brightness(img_pil).enhance(brightness)
    if contrast != 1.0:
        img_pil = ImageEnhance.Contrast(img_pil).enhance(contrast)
    if sharpness != 1.0:
        img_pil = ImageEnhance.Sharpness(img_pil).enhance(sharpness)

    return img_pil


def generar_metadata(
    ruta_original: Path,
    ruta_salida: Path,
    face_coords,
    crop_info: dict,
    detection_method: str,
) -> dict:
    """
    Genera metadata JSON para la imagen procesada.

    Args:
        ruta_original: Ruta de la imagen original
        ruta_salida: Ruta de la imagen procesada
        face_coords: Coordenadas del rostro detectado (x, y, w, h) o None
        crop_info: Info del recorte (x1, y1, crop_w, crop_h)
        detection_method: Método usado ("face" o "center")

    Returns:
        Dict con metadata
    """
    metadata = {
        "source_file": str(ruta_original.name),
        "source_path": str(ruta_original.parent),
        "detection_method": detection_method,
        "crop_box": {
            "x1": crop_info["x1"],
            "y1": crop_info["y1"],
            "width": crop_info["crop_w"],
            "height": crop_info["crop_h"],
        },
        "output_size": {
            "width": crop_info.get("target_w", DEFAULT_WIDTH),
            "height": crop_info.get("target_h", DEFAULT_HEIGHT),
        },
        "enhancements": {
            "brightness": 1.05,
            "contrast": 1.1,
            "sharpness": 1.2,
        },
        "processed_at": datetime.now().isoformat(),
    }

    if face_coords is not None:
        x, y, w, h = face_coords
        metadata["face_detected"] = {
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
        }

    return metadata


def procesar_recorte_inteligente(
    min_size: int = DEFAULT_MIN_SIZE,
    blur_threshold: float = DEFAULT_BLUR_THRESHOLD,
    target_width: int = DEFAULT_WIDTH,
    target_height: int = DEFAULT_HEIGHT,
    zoom_factor: float = DEFAULT_ZOOM_FACTOR,
    apply_enhancements: bool = True,
    output_format: str = "jpeg",
    save_metadata: bool = True,
):
    """
    Pipeline principal: recorre imágenes, detecta rostros, recorta y guarda.

    Args:
        min_size: Tamaño mínimo de imagen para procesar (px)
        blur_threshold: Umbral de desenfoque (varianza Laplaciano)
        target_width: Ancho final del retrato
        target_height: Alto final del retrato
        zoom_factor: Factor de zoom vertical para detección facial
        apply_enhancements: Si True, aplica mejoras visuales
        output_format: Formato de salida ("jpeg", "png", o "both")
        save_metadata: Si True, genera archivo .json sidecar por imagen
    """
    # Cargar cascadas
    cascades = load_cascades()

    # Stats
    stats = {
        "total_processed": 0,
        "total_skipped_small": 0,
        "total_skipped_blurry": 0,
        "total_face_detected": 0,
        "total_center_fallback": 0,
        "total_failed": 0,
        "total_success": 0,
    }

    log.info(f"Iniciando recorte a {target_width}x{target_height}...")
    log.info(f"  Filtros: min_size={min_size}px, blur_threshold={blur_threshold}")
    log.info(f"  Detección facial: {len(cascades)} cascadas Haar")
    log.info(f"  Formato output: {output_format}")

    if not BASE_DIR.exists():
        log.error(f"Directorio no encontrado: {BASE_DIR}")
        return stats

    for raiz, subdirs, archivos in os.walk(BASE_DIR):
        subdirs[:] = [d for d in subdirs if d not in EXCLUDE_FOLDERS]

        if raiz == str(BASE_DIR):
            continue

        for archivo in archivos:
            if not archivo.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            ruta_completa = Path(raiz) / archivo
            stats["total_processed"] += 1

            # Ruta de salida manteniendo estructura
            ruta_salida_carpeta = Path(
                str(raiz).replace(str(BASE_DIR), str(OUTPUT_DIR), 1)
            )
            ruta_salida_carpeta.mkdir(parents=True, exist_ok=True)

            # --- Filtro 1: Tamaño mínimo ---
            if min_size > 0 and is_image_too_small(ruta_completa, min_size):
                log.warning(f"  [SKIP-SMALL] {archivo} (< {min_size}px)")
                stats["total_skipped_small"] += 1
                continue

            # --- Filtro 2: Detección de blur ---
            if blur_threshold > 0 and is_image_blurry(ruta_completa, blur_threshold):
                log.warning(f"  [SKIP-BLUR] {archivo} (blurry)")
                stats["total_skipped_blurry"] += 1
                continue

            try:
                # 1. Cargar imagen con OpenCV para detección facial
                img_cv = cv2.imread(str(ruta_completa))
                if img_cv is None:
                    raise ValueError("Imagen no pudo ser cargada por OpenCV.")

                # 2. Detectar rostro con múltiples cascadas
                face_result = detect_face(img_cv, cascades)

                if face_result is not None:
                    x, y, w, h, cascade_name = face_result
                    face_coords = (x, y, w, h)
                    stats["total_face_detected"] += 1
                    log.debug(f"  [FACE] {archivo} (via {cascade_name})")
                else:
                    face_coords = None
                    stats["total_center_fallback"] += 1
                    log.debug(f"  [CENTER] {archivo} (no face detected, using center)")

                # 3. Calcular crop box
                x1, y1, crop_w, crop_h, detection = calcular_crop_box(
                    img_cv.shape, face_coords, zoom_factor, target_width, target_height
                )

                crop_info = {
                    "x1": int(x1),
                    "y1": int(y1),
                    "crop_w": int(crop_w),
                    "crop_h": int(crop_h),
                    "target_w": target_width,
                    "target_h": target_height,
                }

                # 4. Abrir con PIL y procesar
                Image.MAX_IMAGE_PIXELS = None
                img_pil = Image.open(ruta_completa)

                # Convertir RGBA/P a RGB
                if img_pil.mode in ("RGBA", "P"):
                    img_pil = img_pil.convert("RGB")

                # Recortar
                img_recortada = img_pil.crop((x1, y1, x1 + crop_w, y1 + crop_h))

                # Redimensionar
                img_final = img_recortada.resize(
                    (target_width, target_height), Image.Resampling.LANCZOS
                )

                # Mejoras visuales
                if apply_enhancements:
                    img_final = aplicar_mejoras(img_final)

                # 5. Guardar en formato(s)
                stem = Path(archivo).stem

                if output_format in ("jpeg", "both"):
                    ruta_jpg = ruta_salida_carpeta / f"{stem}.jpg"
                    img_final.save(ruta_jpg, "JPEG", quality=95)

                if output_format in ("png", "both"):
                    ruta_png = ruta_salida_carpeta / f"{stem}.png"
                    img_final.save(ruta_png, "PNG")

                # 6. Guardar metadata sidecar
                if save_metadata:
                    metadata = generar_metadata(
                        ruta_completa,
                        ruta_salida_carpeta,
                        face_coords,
                        crop_info,
                        detection,
                    )
                    ruta_json = ruta_salida_carpeta / f"{stem}.json"
                    with open(ruta_json, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)

                stats["total_success"] += 1
                log.info(f"  [OK] {archivo} ({detection})")

            except Exception as e:
                log.error(f"  [FAIL] {archivo}: {e}")
                stats["total_failed"] += 1

    # Resumen
    log.info("\n" + "=" * 50)
    log.info("RESUMEN DE PROCESAMIENTO")
    log.info("=" * 50)
    log.info(f"Total procesadas: {stats['total_processed']}")
    log.info(f"Exitosas: {stats['total_success']}")
    log.info(f"Fallidas: {stats['total_failed']}")
    log.info(f"Saltadas (tamaño): {stats['total_skipped_small']}")
    log.info(f"Saltadas (borrosas): {stats['total_skipped_blurry']}")
    log.info(f"Detección facial: {stats['total_face_detected']}")
    log.info(f"Fallback centro: {stats['total_center_fallback']}")
    log.info(f"Output: {OUTPUT_DIR}")

    return stats


def main():
    """CLI para el pipeline de procesamiento."""
    parser = argparse.ArgumentParser(
        description="Pipeline de procesamiento de retratos"
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=DEFAULT_MIN_SIZE,
        help=f"Tamaño mínimo de imagen en px (default: {DEFAULT_MIN_SIZE})",
    )
    parser.add_argument(
        "--blur-threshold",
        type=float,
        default=DEFAULT_BLUR_THRESHOLD,
        help=f"Umbral de blur Laplaciano (default: {DEFAULT_BLUR_THRESHOLD}, 0=deshabilitado)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help=f"Ancho final (default: {DEFAULT_WIDTH})",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_HEIGHT,
        help=f"Alto final (default: {DEFAULT_HEIGHT})",
    )
    parser.add_argument(
        "--zoom",
        type=float,
        default=DEFAULT_ZOOM_FACTOR,
        help=f"Factor zoom vertical (default: {DEFAULT_ZOOM_FACTOR})",
    )
    parser.add_argument(
        "--no-enhance", action="store_true", help="No aplicar mejoras visuales"
    )
    parser.add_argument(
        "--output-format",
        choices=["jpeg", "png", "both"],
        default="jpeg",
        help="Formato de salida (default: jpeg)",
    )
    parser.add_argument(
        "--no-metadata", action="store_true", help="No generar archivos .json sidecar"
    )

    args = parser.parse_args()

    procesar_recorte_inteligente(
        min_size=args.min_size,
        blur_threshold=args.blur_threshold,
        target_width=args.width,
        target_height=args.height,
        zoom_factor=args.zoom,
        apply_enhancements=not args.no_enhance,
        output_format=args.output_format,
        save_metadata=not args.no_metadata,
    )


if __name__ == "__main__":
    main()
