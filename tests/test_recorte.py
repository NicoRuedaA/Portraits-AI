"""
Tests para recortar_retratos.py

Testea las funciones de procesamiento de imágenes:
- aplicar_mejoras: brillo, contraste, nitidez
- calcular_crop_box: detección facial y fallback a centro
- Conversión RGBA → RGB
- is_image_too_small: filtro de tamaño mínimo
- generar_metadata: JSON sidecar
- Dimensiones objetivo y ratio de aspecto
"""

import json
import sys
from pathlib import Path

from PIL import Image

# Añadir python/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from recortar_retratos import (
    DEFAULT_WIDTH,
    DEFAULT_HEIGHT,
    DEFAULT_ZOOM_FACTOR,
    DEFAULT_MIN_SIZE,
    DEFAULT_BLUR_THRESHOLD,
    aplicar_mejoras,
    calcular_crop_box,
    generar_metadata,
    HAAR_CASCADES,
    EXCLUDE_FOLDERS,
)


class TestAplicarMejoras:
    """Tests para la función aplicar_mejoras()."""

    def test_returns_pil_image(self):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = aplicar_mejoras(img)
        assert isinstance(result, Image.Image)

    def test_output_same_size_as_input(self):
        img = Image.new("RGB", (200, 300), color=(100, 100, 100))
        result = aplicar_mejoras(img)
        assert result.size == (200, 300)

    def test_brightness_enhancement(self):
        dark = Image.new("RGB", (100, 100), color=(50, 50, 50))
        result = aplicar_mejoras(dark)
        result_pixels = list(result.getdata())
        original_pixels = list(dark.getdata())
        assert result_pixels != original_pixels

    def test_handles_white_image(self):
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = aplicar_mejoras(img)
        assert isinstance(result, Image.Image)

    def test_handles_black_image(self):
        img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        result = aplicar_mejoras(img)
        assert isinstance(result, Image.Image)

    def test_custom_brightness(self):
        img = Image.new("RGB", (100, 100), color=(100, 100, 100))
        result = aplicar_mejoras(img, brightness=1.2)
        assert isinstance(result, Image.Image)

    def test_no_enhancement_when_identity(self):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = aplicar_mejoras(img, brightness=1.0, contrast=1.0, sharpness=1.0)
        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)


class TestCalcularCropBox:
    """Tests para calcular_crop_box()."""

    def test_crop_ratio_matches_target(self):
        target_ratio = DEFAULT_WIDTH / DEFAULT_HEIGHT
        assert abs(target_ratio - 2 / 3) < 0.01

    def test_factor_zoom_is_reasonable(self):
        assert 0 < DEFAULT_ZOOM_FACTOR < 1

    def test_center_fallback_with_no_face(self):
        img_h, img_w = 1000, 800
        result = calcular_crop_box(
            (img_h, img_w, 3), None, DEFAULT_ZOOM_FACTOR, DEFAULT_WIDTH, DEFAULT_HEIGHT
        )
        x1, y1, crop_w, crop_h, detection = result
        assert detection == "center"
        assert crop_w <= img_w
        assert crop_h <= img_h

    def test_face_detection_shifts_center(self):
        img_h, img_w = 1000, 800
        face_coords = (200, 150, 100, 120)
        result = calcular_crop_box(
            (img_h, img_w, 3),
            face_coords,
            DEFAULT_ZOOM_FACTOR,
            DEFAULT_WIDTH,
            DEFAULT_HEIGHT,
        )
        x1, y1, crop_w, crop_h, detection = result
        assert detection == "face"
        assert crop_w <= img_w
        assert crop_h <= img_h

    def test_narrow_image_adjusts(self):
        """Cuando la imagen es más angosta que el ratio target."""
        img_h, img_w = 1000, 400
        result = calcular_crop_box(
            (img_h, img_w, 3), None, DEFAULT_ZOOM_FACTOR, DEFAULT_WIDTH, DEFAULT_HEIGHT
        )
        _, _, crop_w, crop_h, _ = result
        assert crop_w <= img_w
        assert crop_h <= img_h

    def test_crop_box_non_negative(self):
        """Los valores del crop box nunca deben ser negativos."""
        img_shape = (500, 500, 3)
        face_coords = (10, 10, 50, 50)
        result = calcular_crop_box(
            img_shape, face_coords, DEFAULT_ZOOM_FACTOR, DEFAULT_WIDTH, DEFAULT_HEIGHT
        )
        x1, y1, crop_w, crop_h, _ = result
        assert x1 >= 0
        assert y1 >= 0


class TestImageConversion:
    """Tests para la conversión RGBA → RGB."""

    def test_rgba_to_rgb(self):
        img_rgba = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        assert img_rgba.mode == "RGBA"
        img_rgb = img_rgba.convert("RGB")
        assert img_rgb.mode == "RGB"

    def test_palette_mode_to_rgb(self):
        img_p = Image.new("P", (100, 100))
        assert img_p.mode == "P"
        img_rgb = img_p.convert("RGB")
        assert img_rgb.mode == "RGB"


class TestTargetDimensions:
    """Tests para las dimensiones objetivo."""

    def test_target_dimensions(self):
        assert DEFAULT_WIDTH == 512
        assert DEFAULT_HEIGHT == 768

    def test_aspect_ratio(self):
        ratio = DEFAULT_WIDTH / DEFAULT_HEIGHT
        assert abs(ratio - 2 / 3) < 0.01


class TestGenerarMetadata:
    """Tests para generar_metadata()."""

    def test_metadata_with_face(self):
        ruta_original = Path(
            "Retratos/Siglo XVII/Francesa/Luis XIV/Luis_XIV_portrait.jpg"
        )
        ruta_salida = Path("01_RECORTE_FINAL/Siglo XVII/Francesa/Luis XIV")
        face_coords = (200, 150, 100, 120)
        crop_info = {
            "x1": 100,
            "y1": 50,
            "crop_w": 300,
            "crop_h": 450,
            "target_w": DEFAULT_WIDTH,
            "target_h": DEFAULT_HEIGHT,
        }
        metadata = generar_metadata(
            ruta_original, ruta_salida, face_coords, crop_info, "face"
        )
        assert metadata["detection_method"] == "face"
        assert "face_detected" in metadata
        assert metadata["face_detected"]["x"] == 200
        assert metadata["face_detected"]["width"] == 100
        assert metadata["output_size"]["width"] == DEFAULT_WIDTH
        assert metadata["crop_box"]["x1"] == 100

    def test_metadata_without_face(self):
        ruta_original = Path("Retratos/test.jpg")
        ruta_salida = Path("output")
        crop_info = {
            "x1": 0,
            "y1": 0,
            "crop_w": 300,
            "crop_h": 450,
            "target_w": 512,
            "target_h": 768,
        }
        metadata = generar_metadata(
            ruta_original, ruta_salida, None, crop_info, "center"
        )
        assert metadata["detection_method"] == "center"
        assert "face_detected" not in metadata

    def test_metadata_has_enhancements(self):
        ruta_original = Path("test.jpg")
        ruta_salida = Path("output")
        crop_info = {
            "x1": 0,
            "y1": 0,
            "crop_w": 300,
            "crop_h": 450,
            "target_w": 512,
            "target_h": 768,
        }
        metadata = generar_metadata(
            ruta_original, ruta_salida, None, crop_info, "center"
        )
        assert "enhancements" in metadata
        assert metadata["enhancements"]["brightness"] == 1.05
        assert metadata["enhancements"]["contrast"] == 1.1
        assert metadata["enhancements"]["sharpness"] == 1.2

    def test_metadata_is_json_serializable(self):
        ruta_original = Path("test.jpg")
        ruta_salida = Path("output")
        crop_info = {
            "x1": 0,
            "y1": 0,
            "crop_w": 300,
            "crop_h": 450,
            "target_w": 512,
            "target_h": 768,
        }
        metadata = generar_metadata(
            ruta_original, ruta_salida, None, crop_info, "center"
        )
        json_str = json.dumps(metadata, ensure_ascii=False)
        assert len(json_str) > 0


class TestQualityFilters:
    """Tests para filtros de calidad."""

    def test_default_min_size(self):
        assert DEFAULT_MIN_SIZE == 200

    def test_default_blur_threshold(self):
        assert DEFAULT_BLUR_THRESHOLD == 50.0

    def test_small_image_detected(self, tmp_path):
        """Imágenes pequeñas deben ser filtradas."""
        from recortar_retratos import is_image_too_small

        small_img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        small_path = tmp_path / "small.jpg"
        small_img.save(small_path)

        assert is_image_too_small(small_path, 200) is True

    def test_large_image_passes(self, tmp_path):
        """Imágenes grandes deben pasar el filtro."""
        from recortar_retratos import is_image_too_small

        large_img = Image.new("RGB", (800, 1000), color=(128, 128, 128))
        large_path = tmp_path / "large.jpg"
        large_img.save(large_path)

        assert is_image_too_small(large_path, 200) is False

    def test_haar_cascades_defined(self):
        assert len(HAAR_CASCADES) >= 1

    def test_exclude_folders_defined(self):
        assert "venv" in EXCLUDE_FOLDERS
        assert "01_RECORTE_FINAL" in EXCLUDE_FOLDERS
        assert "00_DESCARTADOS" in EXCLUDE_FOLDERS
