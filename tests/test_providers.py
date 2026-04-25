"""
Tests para providers.py

Testea la arquitectura de providers y los providers concretos.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

# Test solo si providers está disponible
try:
    from providers import (
        PortraitProvider,
        WikipediaProvider,
        WikimediaCommonsProvider,
        CombinedProvider,
        create_provider,
        PortraitImage,
        HEADERS,
    )

    PROVIDERS_IMPORTED = True
except ImportError:
    PROVIDERS_IMPORTED = False


pytestmark = pytest.mark.skipif(
    not PROVIDERS_IMPORTED, reason="providers.py not available"
)


class TestPortraitImage:
    """Tests para el dataclass PortraitImage."""

    def test_create_basic(self):
        img = PortraitImage(
            url="https://example.com/portrait.jpg",
            title="Portrait of King",
            source="wikipedia:en",
        )
        assert img.url == "https://example.com/portrait.jpg"
        assert img.title == "Portrait of King"
        assert img.source == "wikipedia:en"

    def test_create_with_dimensions(self):
        img = PortraitImage(
            url="https://example.com/portrait.jpg",
            title="Portrait",
            source="wikimedia-commons",
            width=1000,
            height=1500,
            thumbnail_url="https://example.com/thumb.jpg",
        )
        assert img.width == 1000
        assert img.height == 1500
        assert img.thumbnail_url == "https://example.com/thumb.jpg"


class TestWikipediaProvider:
    """Tests para WikipediaProvider."""

    def test_init(self):
        provider = WikipediaProvider(lang="es")
        assert provider.lang == "es"
        assert provider.max_images == 5

    def test_get_name(self):
        provider = WikipediaProvider(lang="en")
        assert provider.get_name() == "wikipedia:en"

    @patch("wikipedia.page")
    def test_search_with_filters(self, mock_page):
        """Debe filtrar URLs por keywords."""
        mock_page.return_value = MagicMock(
            images=[
                "https://upload.wikimedia.org/Louis_XIV_portrait.jpg",
                "https://upload.wikimedia.org/Louis_XIV_arms.svg",
                "https://upload.wikimedia.org/Map.png",
                "https://upload.wikimedia.org/Louis_XIV_painting.jpg",
            ]
        )

        provider = WikipediaProvider(lang="en")
        images = provider.search(
            "Louis XIV",
            keywords=["portrait", "painting"],
            exclude_keywords=["arms", "map"],
        )

        # Solo portrait y painting deben pasar
        assert len(images) >= 1
        assert any("portrait" in i.url.lower() for i in images)

    @patch("wikipedia.page")
    def test_search_empty_on_error(self, mock_page):
        """Debe retornar lista vacía en caso de error."""
        import wikipedia.exceptions

        mock_page.side_effect = wikipedia.exceptions.PageError("Test")

        provider = WikipediaProvider()
        images = provider.search("NonExistent", ["portrait"], [])

        assert images == []


class TestWikimediaCommonsProvider:
    """Tests para WikimediaCommonsProvider."""

    def test_init(self):
        provider = WikimediaCommonsProvider(lang="en")
        assert provider.lang == "en"
        assert provider.max_images == 5

    def test_get_name(self):
        provider = WikimediaCommonsProvider(lang="es")
        assert provider.get_name() == "wikimedia-commons"

    def test_api_url(self):
        assert "wikimedia.org/w/api.php" in WikimediaCommonsProvider.API_URL


class TestCombinedProvider:
    """Tests para CombinedProvider."""

    def test_init(self):
        providers = [
            WikipediaProvider(lang="en"),
            WikimediaCommonsProvider(lang="en"),
        ]
        combined = CombinedProvider(providers, min_results=1)
        assert len(combined.providers) == 2
        assert combined.min_results == 1

    def test_get_name(self):
        providers = [WikipediaProvider(lang="en")]
        combined = CombinedProvider(providers)
        combined.get_name() == "combined:wikipedia:en"


class TestCreateProvider:
    """Tests para el factory create_provider."""

    def test_create_wikipedia(self):
        provider = create_provider("wikipedia", lang="es")
        assert isinstance(provider, WikipediaProvider)
        assert provider.lang == "es"

    def test_create_wikimedia(self):
        provider = create_provider("wikimedia", lang="en")
        assert isinstance(provider, WikimediaCommonsProvider)

    def test_create_combined(self):
        provider = create_provider("combined", lang="en")
        assert isinstance(provider, CombinedProvider)

    def test_invalid_provider(self):
        with pytest.raises(ValueError):
            create_provider("invalid")
