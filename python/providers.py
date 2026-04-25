#!/usr/bin/env python3
"""
providers.py — Arquitectura de Providers para Portraits-AI.

Patrón Strategy: múltiples fuentes de imágenes con interfaz común.

Providers disponibles:
- WikipediaProvider: Scraping desde páginas de Wikipedia
- WikimediaCommonsProvider: API de Wikimedia Commons (más imágenes, mejor calidad)

Uso:
    provider = WikipediaProvider(lang="es")
    images = provider.search("Luis XIV de Francia")

    # O usar el factory:
    provider = create_provider("wikimedia", lang="en")
"""

import abc
import logging
from dataclasses import dataclass
from typing import Optional

import requests
import wikipedia

# Logging
log = logging.getLogger(__name__)

# Headers para requests
HEADERS = {
    "User-Agent": "PortraitsAI/1.0 (https://github.com/NicoRuedaA/Portraits-AI; academic/educational use)"
}


@dataclass
class PortraitImage:
    """Representa una imagen encontrada."""

    url: str
    title: str  # Título de la imagen en la fuente
    source: str  # Provider que la encontró
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: Optional[str] = None


class PortraitProvider(abc.ABC):
    """Abstract Base Class para providers de imágenes."""

    def __init__(self, lang: str = "es"):
        """
        Inicializar provider.

        Args:
            lang: Código de idioma para búsquedas
        """
        self.lang = lang

    @abc.abstractmethod
    def search(
        self, monarch_name: str, keywords: list, exclude_keywords: list
    ) -> list[PortraitImage]:
        """
        Buscar imágenes de un monarca.

        Args:
            monarch_name: Nombre del monarca para búsqueda
            keywords: Keywords positives (deben estar en la URL)
            exclude_keywords: Keywords a excluir

        Returns:
            Lista de PortraitImage encontradas
        """
        pass

    @abc.abstractmethod
    def get_name(self) -> str:
        """Nombre del provider."""
        pass


class WikipediaProvider(PortraitProvider):
    """Provider que busca imágenes desde páginas de Wikipedia."""

    def __init__(self, lang: str = "es", max_images: int = 5):
        super().__init__(lang)
        self.max_images = max_images
        wikipedia.set_lang(lang)

    def get_name(self) -> str:
        return f"wikipedia:{self.lang}"

    def search(
        self, monarch_name: str, keywords: list, exclude_keywords: list
    ) -> list[PortraitImage]:
        """Buscar imágenes en Wikipedia."""
        images = []

        try:
            page = wikipedia.page(monarch_name, auto_suggest=False)
            page_images = page.images or []

            for img_url in page_images:
                img_lower = img_url.lower()

                # Filtrar por extensión
                if not any(
                    img_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png")
                ):
                    continue

                # Keyword positiva requerida
                if keywords and not any(k in img_lower for k in keywords):
                    continue

                # Excludes
                if exclude_keywords and any(k in img_lower for k in exclude_keywords):
                    continue

                images.append(
                    PortraitImage(
                        url=img_url,
                        title=img_url.split("/")[-1],
                        source=self.get_name(),
                    )
                )

                if len(images) >= self.max_images:
                    break

        except wikipedia.exceptions.PageError:
            log.debug(f"Página no encontrada: {monarch_name}")
        except Exception as e:
            log.error(f"Error en WikipediaProvider: {e}")

        return images


class WikimediaCommonsProvider(PortraitProvider):
    """Provider que usa la API de Wikimedia Commons.

    Wikimedia Commons tiene:
    - Más imágenes por artículo
    - Mejores calidades disponibles (originales, no solo thumbnails)
    - Metadata estructurada (artista, fecha, licencia)
    """

    API_URL = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, lang: str = "en", max_images: int = 5):
        super().__init__(lang)
        self.max_images = max_images

    def get_name(self) -> str:
        return "wikimedia-commons"

    def search(
        self, monarch_name: str, keywords: list, exclude_keywords: list
    ) -> list[PortraitImage]:
        """Buscar imágenes en Wikimedia Commons."""
        images = []

        # Construcción de query para Commons
        # Buscar en categorías o en el propio artículo
        search_terms = [monarch_name]

        # Agregar keywords como filtro adicional
        for kw in keywords[:3]:  # Máximo 3 keywords en búsqueda
            if kw.lower() not in ["portrait", "painting"]:
                search_terms.append(kw)

        search_query = " ".join(search_terms)

        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f'"{search_query}" category:painting category:portrait',
            "srlimit": self.max_images * 2,  # Buscar más para filtrar
            "srprop": "size",
            "origin": "*",
        }

        try:
            response = requests.get(
                self.API_URL, params=params, headers=HEADERS, timeout=15
            )
            data = response.json()

            search_results = data.get("query", {}).get("search", [])

            for result in search_results[: self.max_images * 2]:
                # Obtener información de la imagen
                img_params = {
                    "action": "query",
                    "format": "json",
                    "titles": result["title"],
                    "prop": "imageinfo",
                    "iiprop": "url|size",
                    "origin": "*",
                }

                img_response = requests.get(
                    self.API_URL, params=img_params, headers=HEADERS, timeout=10
                )
                img_data = img_response.json()

                pages = img_data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    imageinfo = page_data.get("imageinfo", [])
                    if not imageinfo:
                        continue

                    info = imageinfo[0]
                    img_url = info.get("url", "")
                    thumb_url = info.get("thumburl", "")
                    width = info.get("width")
                    height = info.get("height")

                    img_lower = img_url.lower()

                    # Filtrar por extensión
                    if not any(
                        img_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png")
                    ):
                        continue

                    # Excludes
                    if exclude_keywords and any(
                        k in img_lower for k in exclude_keywords
                    ):
                        continue

                    images.append(
                        PortraitImage(
                            url=img_url,
                            title=result["title"],
                            source=self.get_name(),
                            width=width,
                            height=height,
                            thumbnail_url=thumb_url,
                        )
                    )

                    if len(images) >= self.max_images:
                        break

        except requests.exceptions.RequestException as e:
            log.error(f"Error en Wikimedia Commons API: {e}")
        except Exception as e:
            log.error(f"Error en WikimediaCommonsProvider: {e}")

        return images[: self.max_images]


class CombinedProvider(PortraitProvider):
    """Provider combinado que usa múltiples fuentes.

    Busca en orden de prioridad hasta encontrar imágenes.
    """

    def __init__(self, providers: list[PortraitProvider], min_results: int = 1):
        """
        Args:
            providers: Lista de providers en orden de prioridad
            min_results: Mínimo de imágenes antes de retornar
        """
        # Usar el primer provider para el idioma
        super().__init__(lang=providers[0].lang if providers else "en")
        self.providers = providers
        self.min_results = min_results

    def get_name(self) -> str:
        names = [p.get_name() for p in self.providers]
        return f"combined:{'+'.join(names)}"

    def search(
        self, monarch_name: str, keywords: list, exclude_keywords: list
    ) -> list[PortraitImage]:
        """Buscar en todos los providers hasta tener resultados."""
        all_images = []

        for provider in self.providers:
            log.debug(f"Buscando en {provider.get_name()}...")
            images = provider.search(monarch_name, keywords, exclude_keywords)

            if images:
                all_images.extend(images)
                log.info(f"Encontradas {len(images)} imágenes en {provider.get_name()}")

                if len(all_images) >= self.min_results:
                    break

        return all_images


def create_provider(
    provider_type: str, lang: str = "es", max_images: int = 5
) -> PortraitProvider:
    """
    Factory para crear providers.

    Args:
        provider_type: "wikipedia", "wikimedia", o "combined"
        lang: Código de idioma
        max_images: Máximo de imágenes a retornar

    Returns:
        Instancia de PortraitProvider
    """
    if provider_type == "wikipedia":
        return WikipediaProvider(lang=lang, max_images=max_images)
    elif provider_type == "wikimedia":
        return WikimediaCommonsProvider(lang=lang, max_images=max_images)
    elif provider_type == "combined":
        # Combina Wikipedia + Wikimedia Commons
        providers = [
            WikipediaProvider(lang=lang, max_images=max_images),
            WikimediaCommonsProvider(lang=lang, max_images=max_images),
        ]
        return CombinedProvider(providers, min_results=1)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


if __name__ == "__main__":
    # Ejemplo de uso
    import sys

    if len(sys.argv) < 2:
        print("Usage: python providers.py <monarch_name>")
        sys.exit(1)

    monarch = sys.argv[1]

    print(f"\n=== Buscando: {monarch} ===\n")

    # Wikipedia
    wp = create_provider("wikipedia")
    print(f"Provider: {wp.get_name()}")
    images = wp.search(monarch, ["portrait", "painting"], ["arms", "map", "flag"])
    print(f"Resultados: {len(images)}\n")

    # Wikimedia Commons
    wc = create_provider("wikimedia")
    print(f"Provider: {wc.get_name()}")
    images = wc.search(monarch, ["portrait", "painting"], ["arms", "map", "flag"])
    print(f"Resultados: {len(images)}\n")

    # Combined
    combined = create_provider("combined")
    print(f"Provider: {combined.get_name()}")
    images = combined.search(monarch, ["portrait", "painting"], ["arms", "map", "flag"])
    print(f"Resultados: {len(images)}")
