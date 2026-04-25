"""
Tests para scraper_core.py

Testea las funciones principales del motor de scraping usando mocks
para no llamar a Wikipedia ni hacer requests reales.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Añadir python/ al path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from scraper_core import (
    download_with_retry,
    get_valid_images,
    load_config,
    setup_wikipedia,
    count_portraits,
    MAX_IMAGES_PER_MONARCH,
    MAX_RETRIES,
)


class TestLoadConfig:
    """Tests para load_config()."""

    def test_loads_valid_config(self):
        """Debe cargar monarcas.json correctamente."""
        # Usar la ruta real del proyecto, no la del módulo
        config_path = Path(__file__).parent.parent / "monarcas.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        assert isinstance(config, dict)
        assert len(config) > 0

    def test_config_has_expected_dynasties(self):
        """Las dinastías principales deben estar presentes."""
        config_path = Path(__file__).parent.parent / "monarcas.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        expected = ["Francesa", "Otomana", "Rusa", "Española", "Britanica"]
        for dynasty in expected:
            assert dynasty in config, f"Missing dynasty: {dynasty}"

    def test_config_raises_on_missing_file(self, tmp_path):
        """Debe lanzar FileNotFoundError si no existe el archivo."""
        import scraper_core

        original_config = scraper_core.CONFIG_FILE
        scraper_core.CONFIG_FILE = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            load_config()

        scraper_core.CONFIG_FILE = original_config


class TestSetupWikipedia:
    """Tests para setup_wikipedia()."""

    def test_setup_valid_language(self):
        """Debe configurar idioma válido correctamente."""
        with patch("wikipedia.set_lang") as mock_set_lang:
            setup_wikipedia("es")
            mock_set_lang.assert_called_once_with("es")

    def test_setup_english(self):
        """Debe configurar inglés correctamente."""
        with patch("wikipedia.set_lang") as mock_set_lang:
            setup_wikipedia("en")
            mock_set_lang.assert_called_once_with("en")


class TestGetValidImages:
    """Tests para get_valid_images() con mock de Wikipedia."""

    @patch("wikipedia.page")
    def test_returns_filtered_images(self, mock_page):
        """Debe devolver imágenes que cumplan los filtros."""
        mock_page.return_value = MagicMock(
            images=[
                "https://upload.wikimedia.org/Louis_XIV_portrait.jpg",
                "https://upload.wikimedia.org/Louis_XIV_arms.svg",
                "https://upload.wikimedia.org/Map_of_France.png",
                "https://upload.wikimedia.org/Louis_XIV_painting.jpg",
            ]
        )

        keywords = ["portrait", "painting", "king"]
        exclude = ["arms", "coa", "map", "svg"]

        result = get_valid_images("Louis XIV", keywords, exclude)

        # Solo "portrait" y "painting" deben pasar
        assert any("portrait" in r.lower() for r in result)
        assert any("painting" in r.lower() for r in result)

    @patch("wikipedia.page")
    def test_returns_empty_on_page_error(self, mock_page):
        """Debe devolver lista vacía si la página no existe."""
        import wikipedia.exceptions

        mock_page.side_effect = wikipedia.exceptions.PageError("Test")

        result = get_valid_images("NonExistent", ["portrait"], [])
        assert result == []

    @patch("wikipedia.page")
    def test_limits_to_max_images(self, mock_page):
        """Debe limitar a MAX_IMAGES_PER_MONARCH resultados."""
        # Crear más de MAX_IMAGES_PER_MONARCH URLs válidas
        images = [
            f"https://upload.wikimedia.org/Monarch_{i}_portrait.jpg" for i in range(20)
        ]
        mock_page.return_value = MagicMock(images=images)

        result = get_valid_images("Test", ["portrait"], [])
        assert len(result) <= MAX_IMAGES_PER_MONARCH

    @patch("wikipedia.page")
    def test_no_images_on_page(self, mock_page):
        """Debe devolver lista vacía si la página no tiene imágenes."""
        mock_page.return_value = MagicMock(images=[])

        result = get_valid_images("Test", ["portrait"], [])
        assert result == []


class TestDownloadWithRetry:
    """Tests para download_with_retry() con mock de requests."""

    @patch("requests.get")
    def test_successful_download(self, mock_get, tmp_path):
        """Debe descargar correctamente con status 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_get.return_value = mock_response

        dest = tmp_path / "test_portrait.jpg"
        result = download_with_retry("https://example.com/portrait.jpg", dest)

        assert result["success"] is True
        assert result["attempts"] == 1
        assert dest.exists()

    @patch("requests.get")
    def test_retry_on_timeout(self, mock_get, tmp_path):
        """Debe reintentar después de un timeout."""
        import requests.exceptions

        # Primer intento: timeout, segundo: éxito
        mock_get.side_effect = [
            requests.exceptions.Timeout("Connection timed out"),
            MagicMock(status_code=200, content=b"fake_image_data"),
        ]

        dest = tmp_path / "test_portrait.jpg"
        result = download_with_retry("https://example.com/portrait.jpg", dest)

        assert result["success"] is True
        assert result["attempts"] == 2

    @patch("requests.get")
    def test_fails_after_max_retries(self, mock_get, tmp_path):
        """Debe fallar después de MAX_RETRIES intentos."""
        import requests.exceptions

        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        dest = tmp_path / "test_portrait.jpg"
        result = download_with_retry("https://example.com/portrait.jpg", dest)

        assert result["success"] is False
        assert result["attempts"] == MAX_RETRIES

    @patch("requests.get")
    def test_handles_404(self, mock_get, tmp_path):
        """Debe manejar status 404 correctamente."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        dest = tmp_path / "test_portrait.jpg"
        result = download_with_retry("https://example.com/portrait.jpg", dest)

        assert result["success"] is False
        assert "404" in result["error"]

    @patch("requests.get")
    @patch("time.sleep")  # Speed up test by mocking sleep
    def test_rate_limit_429_triggers_backoff(self, mock_sleep, mock_get, tmp_path):
        """Debe hacer backoff cuando recibe 429 (rate limited)."""
        # Primer intento: rate limited, segundo: éxito
        mock_get.side_effect = [
            MagicMock(status_code=429),
            MagicMock(status_code=200, content=b"fake_image_data"),
        ]

        dest = tmp_path / "test_portrait.jpg"
        result = download_with_retry("https://example.com/portrait.jpg", dest)

        assert result["success"] is True
        assert mock_sleep.called  # Debio esperar


class TestCountPortraits:
    """Tests para count_portraits()."""

    def test_counts_images_in_structure(self, tmp_path):
        """Debe contar imágenes en la estructura de carpetas."""
        import scraper_core

        # Crear estructura de prueba
        siglo = tmp_path / "Siglo XVI" / "Francesa" / "Francisco I 1515-1547"
        siglo.mkdir(parents=True)

        (siglo / "portrait_1.jpg").write_bytes(b"fake")
        (siglo / "portrait_2.jpg").write_bytes(b"fake")
        (siglo / "notes.txt").write_text("not an image")  # No debe contar

        # Mockear BASE_DIR temporalmente
        original_base = scraper_core.BASE_DIR
        scraper_core.BASE_DIR = tmp_path

        try:
            result = count_portraits()
            assert result["total_images"] == 2
        finally:
            scraper_core.BASE_DIR = original_base

    def test_excludes_system_folders(self, tmp_path):
        """Debe excluir carpetas de sistema."""
        import scraper_core

        # Crear carpeta que debe excluirse
        desc = tmp_path / "00_DESCARTADOS" / "test"
        desc.mkdir(parents=True)
        (desc / "bad.jpg").write_bytes(b"fake")

        original_base = scraper_core.BASE_DIR
        scraper_core.BASE_DIR = tmp_path

        try:
            result = count_portraits()
            assert result["total_images"] == 0
        finally:
            scraper_core.BASE_DIR = original_base

    def test_empty_directory(self, tmp_path):
        """Debe devolver ceros si el directorio está vacío."""
        import scraper_core

        original_base = scraper_core.BASE_DIR
        scraper_core.BASE_DIR = tmp_path

        try:
            result = count_portraits()
            assert result["total_images"] == 0
        finally:
            scraper_core.BASE_DIR = original_base
