"""
Tests para la validación del schema de monarcas.json

Verifica que la configuración tenga la estructura correcta:
- Campos requeridos (lang, monarcas)
- Keywords y exclude_keywords son listas
- Cada monarca tiene 4 elementos [nombre, inicio, fin, siglo]
- Los siglos son válidos
- Los años son enteros razonables
"""

import json
from pathlib import Path

import pytest

# Ruta al proyecto
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_FILE = PROJECT_ROOT / "monarcas.json"

# Siglos válidos (formato del proyecto)
VALID_CENTURIES = {
    "Siglo XIV",
    "Siglo XV",
    "Siglo XVI",
    "Siglo XVII",
    "Siglo XVIII",
    "Siglo XIX",
    "Siglo XX",
    "Siglo XIII",
    "Siglo XII",
}

# Campos requeridos en cada dinastía
REQUIRED_DYNASTY_FIELDS = {"lang", "monarcas"}

# Campos opcionales con defaults
OPTIONAL_FIELDS = {"fallback_lang", "keywords", "exclude_keywords"}


@pytest.fixture
def config_data():
    """Carga monarcas.json para los tests."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class TestMonarcasSchema:
    """Valida la estructura general de monarcas.json."""

    def test_config_file_exists(self):
        """El archivo de configuración debe existir."""
        assert CONFIG_FILE.exists(), f"No se encontró {CONFIG_FILE}"

    def test_config_is_valid_json(self):
        """El archivo debe ser JSON válido."""
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_at_least_one_dynasty(self, config_data):
        """Debe haber al menos una dinastía."""
        assert len(config_data) >= 1

    def test_all_dynasties_have_required_fields(self, config_data):
        """Cada dinastía debe tener lang y monarcas."""
        for dynasty_name, dynasty_data in config_data.items():
            # Skip metadata section
            if dynasty_name.startswith("_"):
                continue
            missing = REQUIRED_DYNASTY_FIELDS - set(dynasty_data.keys())
            assert not missing, f"{dynasty_name} missing fields: {missing}"

    def test_lang_is_valid_string(self, config_data):
        """El campo lang debe ser un código de idioma válido."""
        valid_langs = {"es", "en", "fr", "de", "it", "pt", "zh", "ja", "ar", "ru"}
        for dynasty_name, dynasty_data in config_data.items():
            if dynasty_name.startswith("_"):
                continue
            lang = dynasty_data.get("lang", "")
            assert lang in valid_langs, (
                f"{dynasty_name}: lang '{lang}' is not a valid language code"
            )

    def test_fallback_lang_is_valid(self, config_data):
        """El campo fallback_lang debe ser un código de idioma válido si existe."""
        valid_langs = {"es", "en", "fr", "de", "it", "pt", "zh", "ja", "ar", "ru"}
        for dynasty_name, dynasty_data in config_data.items():
            fallback = dynasty_data.get("fallback_lang")
            if fallback is not None:
                assert fallback in valid_langs, (
                    f"{dynasty_name}: fallback_lang '{fallback}' is not valid"
                )

    def test_keywords_are_lists(self, config_data):
        """Keywords y exclude_keywords deben ser listas."""
        for dynasty_name, dynasty_data in config_data.items():
            if "keywords" in dynasty_data:
                assert isinstance(dynasty_data["keywords"], list), (
                    f"{dynasty_name}: keywords must be a list"
                )
            if "exclude_keywords" in dynasty_data:
                assert isinstance(dynasty_data["exclude_keywords"], list), (
                    f"{dynasty_name}: exclude_keywords must be a list"
                )

    def test_keywords_are_non_empty_strings(self, config_data):
        """Cada keyword debe ser un string no vacío."""
        for dynasty_name, dynasty_data in config_data.items():
            keywords = dynasty_data.get("keywords", [])
            for kw in keywords:
                assert isinstance(kw, str) and len(kw) > 0, (
                    f"{dynasty_name}: keyword must be non-empty string, got '{kw}'"
                )

    def test_exclude_keywords_are_non_empty_strings(self, config_data):
        """Cada exclude_keyword debe ser un string no vacío."""
        for dynasty_name, dynasty_data in config_data.items():
            excludes = dynasty_data.get("exclude_keywords", [])
            for kw in excludes:
                assert isinstance(kw, str) and len(kw) > 0, (
                    f"{dynasty_name}: exclude_keyword must be non-empty string"
                )

    def test_at_least_one_keyword_per_dynasty(self, config_data):
        """Cada dinastía debe tener al menos una keyword positiva."""
        for dynasty_name, dynasty_data in config_data.items():
            if "keywords" in dynasty_data:
                assert len(dynasty_data["keywords"]) >= 1, (
                    f"{dynasty_name}: must have at least one keyword"
                )


class TestMonarchData:
    """Valida los datos de cada monarca individual."""

    def test_monarcas_is_list(self, config_data):
        """El campo monarcas debe ser una lista."""
        for dynasty_name, dynasty_data in config_data.items():
            monarcas = dynasty_data.get("monarcas", [])
            assert isinstance(monarcas, list), (
                f"{dynasty_name}: monarcas must be a list"
            )

    def test_each_monarch_has_4_elements(self, config_data):
        """Cada monarca debe ser una lista de 4 elementos: [nombre, inicio, fin, siglo]."""
        for dynasty_name, dynasty_data in config_data.items():
            monarcas = dynasty_data.get("monarcas", [])
            for i, monarch in enumerate(monarcas):
                assert isinstance(monarch, list), (
                    f"{dynasty_name}[{i}]: must be a list, got {type(monarch)}"
                )
                assert len(monarch) == 4, (
                    f"{dynasty_name}[{i}]: must have 4 elements (name, start, end, century), got {len(monarch)}"
                )

    def test_monarch_name_is_string(self, config_data):
        """El nombre del monarca debe ser un string no vacío."""
        for dynasty_name, dynasty_data in config_data.items():
            monarcas = dynasty_data.get("monarcas", [])
            for i, monarch in enumerate(monarcas):
                name = monarch[0]
                assert isinstance(name, str) and len(name) > 0, (
                    f"{dynasty_name}[{i}]: name must be non-empty string"
                )

    def test_monarch_years_are_integers(self, config_data):
        """Los años de inicio y fin deben ser enteros."""
        for dynasty_name, dynasty_data in config_data.items():
            monarcas = dynasty_data.get("monarcas", [])
            for i, monarch in enumerate(monarcas):
                name = monarch[0]
                inicio = monarch[1]
                fin = monarch[2]
                assert isinstance(inicio, int), (
                    f"{name}: start year must be int, got {type(inicio)}"
                )
                assert isinstance(fin, int), (
                    f"{name}: end year must be int, got {type(fin)}"
                )

    def test_monarch_years_are_reasonable(self, config_data):
        """Los años deben estar en un rango razonable (1-2000)."""
        for dynasty_name, dynasty_data in config_data.items():
            monarcas = dynasty_data.get("monarcas", [])
            for i, monarch in enumerate(monarcas):
                name = monarch[0]
                inicio = monarch[1]
                fin = monarch[2]
                assert 1 <= inicio <= 2000, (
                    f"{name}: start year {inicio} is out of range"
                )
                assert 1 <= fin <= 2000, f"{name}: end year {fin} is out of range"

    def test_monarch_end_after_start(self, config_data):
        """El año de fin debe ser posterior al de inicio."""
        for dynasty_name, dynasty_data in config_data.items():
            monarcas = dynasty_data.get("monarcas", [])
            for i, monarch in enumerate(monarcas):
                name = monarch[0]
                inicio = monarch[1]
                fin = monarch[2]
                assert fin >= inicio, (
                    f"{name}: end year ({fin}) must be >= start year ({inicio})"
                )

    def test_monarch_century_is_valid(self, config_data):
        """El siglo debe ser un valor válido del proyecto."""
        for dynasty_name, dynasty_data in config_data.items():
            monarcas = dynasty_data.get("monarcas", [])
            for i, monarch in enumerate(monarcas):
                name = monarch[0]
                siglo = monarch[3]
                assert siglo in VALID_CENTURIES, (
                    f"{name}: century '{siglo}' is not a valid century format"
                )

    def test_no_duplicate_monarch_names(self, config_data):
        """No debe haber nombres duplicados de monarcas dentro de una dinastía."""
        for dynasty_name, dynasty_data in config_data.items():
            monarcas = dynasty_data.get("monarcas", [])
            names = [m[0] for m in monarcas]
            duplicates = [n for n in names if names.count(n) > 1]
            assert len(duplicates) == 0, (
                f"{dynasty_name}: duplicate monarch names: {set(duplicates)}"
            )


class TestCrossDynastyConsistency:
    """Valida consistencia entre dinastías."""

    def test_all_dynasties_have_monarchs(self, config_data):
        """Ninguna dinastía debe tener lista de monarcas vacía."""
        for dynasty_name, dynasty_data in config_data.items():
            # Skip metadata section
            if dynasty_name.startswith("_"):
                continue
            monarcas = dynasty_data.get("monarcas", [])
            assert len(monarcas) > 0, f"{dynasty_name}: has no monarchs defined"

    def test_total_monarch_count(self, config_data):
        """Debe haber un número razonable de monarcas totales."""
        total = sum(
            len(d.get("monarcas", []))
            for d in config_data.values()
            if not d.get("monarcas", [])
        )
        total = sum(
            len(d.get("monarcas", []))
            for d in config_data.values()
            if isinstance(d, dict) and "monarcas" in d
        )
        assert total >= 20, f"Expected at least 20 monarchs, got {total}"

    def test_all_dynasties_have_keywords(self, config_data):
        """Todas las dinastías deben tener keywords definidas."""
        for dynasty_name, dynasty_data in config_data.items():
            # Skip metadata section
            if dynasty_name.startswith("_"):
                continue
            assert "keywords" in dynasty_data, f"{dynasty_name}: missing keywords"
            assert "exclude_keywords" in dynasty_data, (
                f"{dynasty_name}: missing exclude_keywords"
            )
