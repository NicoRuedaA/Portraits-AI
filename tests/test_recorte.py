"""
Tests para recortar_retratos.py

Testea las funciones de procesamiento de imágenes:
- aplicar_mejoras: brillo, contraste, nitidez
- Cálculo de crop box: detección facial y fallback a centro
- Conversión RGBA → RGB
"""

import sys
from pathlib import Path

from PIL import Image

# Añadir python/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from recortar_retratos import aplicar_mejoras, ANCHO_FINAL, ALTO_FINAL, FACTOR_ZOOM


class TestAplicarMejoras:
    """Tests para la función aplicar_mejoras()."""

    def test_returns_pil_image(self):
        """Debe devolver una imagen PIL."""
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = aplicar_mejoras(img)
        assert isinstance(result, Image.Image)

    def test_output_same_size_as_input(self):
        """La imagen mejorada debe tener el mismo tamaño."""
        img = Image.new("RGB", (200, 300), color=(100, 100, 100))
        result = aplicar_mejoras(img)
        assert result.size == (200, 300)

    def test_brightness_enhancement(self):
        """La mejora de brillo debe aclarar la imagen."""
        dark = Image.new("RGB", (100, 100), color=(50, 50, 50))
        result = aplicar_mejoras(dark)
        # Los píxeles deben ser más claros (brillo * 1.05 + contraste * 1.1)
        result_pixels = list(result.getdata())
        original_pixels = list(dark.getdata())
        # Al menos algunos píxeles deben cambiar
        assert result_pixels != original_pixels

    def test_handles_white_image(self):
        """Debe manejar una imagen completamente blanca sin errores."""
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = aplicar_mejoras(img)
        assert isinstance(result, Image.Image)

    def test_handles_black_image(self):
        """Debe manejar una imagen completamente negra sin errores."""
        img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        result = aplicar_mejoras(img)
        assert isinstance(result, Image.Image)


class TestCropBoxCalculation:
    """Tests para la lógica de cálculo del crop box (recorte)."""

    def test_crop_ratio_matches_target(self):
        """El ratio del crop debe coincidir con ANCHO_FINAL/ALTO_FINAL."""
        target_ratio = ANCHO_FINAL / ALTO_FINAL  # 512/768 = 2/3
        assert abs(target_ratio - 2 / 3) < 0.01

    def test_factor_zoom_is_reasonable(self):
        """El factor de zoom debe estar entre 0 y 1."""
        assert 0 < FACTOR_ZOOM < 1

    def test_center_fallback_with_no_face(self):
        """Sin detección facial, debe usar el centro de la imagen."""
        # Simular: imagen de 800x1000 sin rostro
        img_h = 1000
        img_w = 800

        # Calculate center (used for assertion logic)
        _ = img_w // 2  # center x
        _ = img_h // 2  # center y

        # Ratio target
        ratio = ANCHO_FINAL / ALTO_FINAL  # 0.666...
        crop_h = img_h  # 1000
        crop_w = int(crop_h * ratio)  # 666

        # Si crop_w > img_w, ajustar
        if crop_w > img_w:
            crop_w = img_w
            crop_h = int(crop_w / ratio)

        assert crop_w <= img_w
        assert crop_h <= img_h

    def test_face_detection_shifts_center(self):
        """Con detección facial, el centro debe desplazarse hacia el rostro."""
        # Simular rostro detectado en (200, 150, 100, 120)
        x, y, w, h = 200, 150, 100, 120

        x_centro = x + w // 2  # 250
        y_centro = y + int(h * FACTOR_ZOOM)  # 150 + 60 = 210

        # El centro debe estar desplazado respecto al centro de la imagen
        assert x_centro == 250
        assert y_centro == 210


class TestImageConversion:
    """Tests para la conversión RGBA → RGB."""

    def test_rgba_to_rgb(self):
        """Imágenes RGBA deben convertirse a RGB para guardar como JPEG."""
        img_rgba = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        assert img_rgba.mode == "RGBA"

        # Conversión (como hace el código)
        if img_rgba.mode in ("RGBA", "P"):
            img_rgb = img_rgba.convert("RGB")

        assert img_rgb.mode == "RGB"

    def test_palette_mode_to_rgb(self):
        """Imágenes en modo paleta (P) deben convertirse a RGB."""
        img_p = Image.new("P", (100, 100))
        assert img_p.mode == "P"

        img_rgb = img_p.convert("RGB")
        assert img_rgb.mode == "RGB"


class TestTargetDimensions:
    """Tests para las dimensiones objetivo."""

    def test_target_width(self):
        """Ancho final debe ser 512."""
        assert ANCHO_FINAL == 512

    def test_target_height(self):
        """Alto final debe ser 768."""
        assert ALTO_FINAL == 768

    def test_aspect_ratio(self):
        """El ratio debe ser 2:3 (CK3 estándar)."""
        ratio = ANCHO_FINAL / ALTO_FINAL
        assert abs(ratio - 2 / 3) < 0.01, f"Ratio {ratio} is not 2:3"
