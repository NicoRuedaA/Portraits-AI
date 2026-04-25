#!/usr/bin/env python3
"""
dataset.py — Herramientas para preparación de dataset de entrenamiento.

Genera:
- dataset.yaml para Kohya LoRA / Stable Diffusion
- train/val/test splits
- Metadata consolidado por dinastía

Uso:
    python dataset.py                  # Generar splits
    python dataset.py --yaml          # Generar dataset.yaml
    python dataset.py --augment       # Preparar augmentation
    python dataset.py --validate      # Validar estructura
    python dataset.py --stats         # Mostrar estadísticas
"""

import argparse
import json
import logging
import os
import random
import shutil
from collections import Counter
from pathlib import Path


# --- CONFIGURACIÓN ---
BASE_DIR = Path(__file__).resolve().parent.parent / "Retratos"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "01_RECORTE_FINAL"
SPLITS_DIR = Path(__file__).resolve().parent.parent / "dataset"

# Default splits
DEFAULT_SPLITS = {"train": 0.8, "val": 0.1, "test": 0.1}

# Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def collect_images(output_dir: Path) -> list[dict]:
    """
    Recolecta todas las imágenes procesadas con su metadata.

    Returns:
        Lista de dicts con {image_path, metadata, dynasty, century, monarch}
    """
    images = []

    if not output_dir.exists():
        log.error(f"Output dir no existe: {output_dir}")
        return images

    for siglo_dir in output_dir.iterdir():
        if not siglo_dir.is_dir() or siglo_dir.name.startswith("."):
            continue
        siglo = siglo_dir.name

        for dyn_dir in siglo_dir.iterdir():
            if not dyn_dir.is_dir():
                continue
            dynasty = dyn_dir.name

            for img_file in dyn_dir.iterdir():
                if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                    continue

                # Buscar metadata sidecar
                metadata = {}
                json_file = img_file.with_suffix(".json")
                if json_file.exists():
                    with open(json_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                # Extraer nombre del monarca del path
                parts = img_file.parent.name.split(" ")
                if len(parts) >= 2:
                    # "Nombre 1328-1350" -> "Nombre"
                    monarch = (
                        " ".join(parts[:-1])
                        if parts[-1].count("-")
                        else img_file.parent.name
                    )
                else:
                    monarch = img_file.parent.name

                images.append(
                    {
                        "path": str(img_file),
                        "rel_path": str(img_file.relative_to(output_dir)),
                        "metadata": metadata,
                        "dynasty": dynasty,
                        "century": siglo,
                        "monarch": monarch,
                    }
                )

    log.info(f"Recolectadas {len(images)} imágenes")
    return images


def create_splits(images: list[dict], splits: dict = None, seed: int = 42) -> dict:
    """
    Creates train/val/test splits.

    Args:
        images: Lista de imágenes
        splits: Dict con proporciones {train: 0.8, val: 0.1, test: 0.1}
        seed: Random seed para reproducibilidad

    Returns:
        Dict con {train: [...], val: [...], test: [...]}
    """
    random.seed(seed)

    if splits is None:
        splits = DEFAULT_SPLITS

    total = sum(splits.values())
    if abs(total - 1.0) > 0.01:
        log.warning(f"Splits sum to {total}, normalizing...")
        splits = {k: v / total for k, v in splits.items()}

    # Agrupar por dinastía para mantener balance
    by_dynasty = {}
    for img in images:
        dyn = img["dynasty"]
        if dyn not in by_dynasty:
            by_dynasty[dyn] = []
        by_dynasty[dyn].append(img)

    result = {"train": [], "val": [], "test": []}

    for dynasty, dynasty_images in by_dynasty.items():
        random.shuffle(dynasty_images)
        n = len(dynasty_images)

        n_train = int(n * splits["train"])
        n_val = int(n * splits["val"])

        result["train"].extend(dynasty_images[:n_train])
        result["val"].extend(dynasty_images[n_train : n_train + n_val])
        result["test"].extend(dynasty_images[n_train + n_val :])

    # Verificar proporciones
    total = len(images)
    for split_name, split_images in result.items():
        pct = len(split_images) / total * 100
        log.info(f"  {split_name}: {len(split_images)} ({pct:.1f}%)")

    return result


def generate_yaml(images: list[dict], output_path: Path):
    """
    Genera dataset.yaml para Kohya LoRA / SD training.

    Formato:
    - train_dir: /path/to/train
    - val_dir: /path/to/val
    - caption_extension: .txt
    - ...
    """
    yaml_content = """# Dataset Configuration for Stable Diffusion / LoRA Training
# Generated by Portraits-AI

# Base directories
# Note: Use absolute paths for training

# Image directories are created in the dataset/ folder:
#   dataset/
#   ├── train/
#   ├── val/
#   └── test/

# Prompt template for images
# Caption format: [monarch_name], [dynasty], [century]
prompt_template: "[monarch], [dynasty] monarch, [century]"

# Class labels for regularization (optional)
# class_labels:
#   monarch: "historical monarch portrait"
#   dynasty: "historical dynasty"
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    log.info(f"Generado: {output_path}")


def generate_kohya_reg_yaml(output_dir: Path) -> Path:
    """
    Genera archivo de regularización de clases para Kohya.

    Genera una estructura donde cada clase (dinastía) tiene una imagen
    de regularization.
    """
    # Agrupar por dinastía
    by_dynasty = {}
    for siglo_dir in OUTPUT_DIR.iterdir():
        if not siglo_dir.is_dir():
            continue
        for dyn_dir in siglo_dir.iterdir():
            if not dyn_dir.is_dir():
                continue
            dyn = dyn_dir.name
            imgs = list(dyn_dir.glob("*.jpg")) + list(dyn_dir.glob("*.png"))
            if imgs:
                by_dynasty[dyn] = imgs[0]  # Primera imagen

    # Crear directorio de regularización
    reg_dir = output_dir / "reg"
    reg_dir.mkdir(exist_ok=True)

    # Copiar imágenes de regularización
    for dyn, src_img in by_dynasty.items():
        dst = reg_dir / f"{dyn}.jpg"
        shutil.copy2(src_img, dst)

        # Generar caption
        caption_file = reg_dir / f"{dyn}.txt"
        with open(caption_file, "w") as f:
            f.write(f"{dyn} monarch\n")

    log.info(f"Regularización images: {len(by_dynasty)} dynasties")
    return reg_dir


def create_symlinks(splits: dict, dataset_dir: Path):
    """
    Crea symlinks train/val/test apuntando a las imágenes reales.

    Esto evita duplicar imágenes en disco.
    """
    for split_name, images in splits.items():
        split_dir = dataset_dir / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        for img_data in images:
            img_path = OUTPUT_DIR / img_data["rel_path"]

            if not img_path.exists():
                log.warning(f"Imagen no encontrada: {img_path}")
                continue

            # Nombre del link: dynasty_monarch_001.jpg
            dynasty = img_data["dynasty"]
            monarch = img_data["monarch"].replace(" ", "_")
            link_name = f"{dynasty}_{monarch}_{img_path.stem}.jpg"
            link_path = split_dir / link_name

            try:
                os.symlink(img_path.resolve(), link_path)
            except FileExistsError:
                pass

    log.info(f"Splits creados en {dataset_dir}")


def show_stats(images: list[dict]):
    """Muestra estadísticas del dataset."""
    print("\n=== ESTADÍSTICAS DEL DATASET ===")

    # Por dinastía
    by_dynasty = Counter(i["dynasty"] for i in images)
    print(f"\nPor dinastía ({len(by_dynasty)}):")
    for dyn, count in sorted(by_dynasty.items(), key=lambda x: -x[1]):
        print(f"  {dyn}: {count}")

    # Por siglo
    by_century = Counter(i["century"] for i in images)
    print(f"\nPor siglo ({len(by_century)}):")
    for sig, count in sorted(by_century.items()):
        print(f"  {sig}: {count}")

    # Total
    print(f"\nTotal: {len(images)} imágenes")

    # Con/sin metadata
    with_meta = sum(1 for i in images if i["metadata"])
    without_meta = len(images) - with_meta
    print(f"Con metadata: {with_meta}, sin: {without_meta}")


def main():
    """CLI"""
    parser = argparse.ArgumentParser(description="Dataset preparation tools")
    parser.add_argument(
        "--splits", action="store_true", help="Crear splits train/val/test"
    )
    parser.add_argument("--yaml", action="store_true", help="Generar dataset.yaml")
    parser.add_argument(
        "--kohya-reg", action="store_true", help="Generar reg images para Kohya"
    )
    parser.add_argument(
        "--symlinks", action="store_true", help="Crear symlinks a splits"
    )
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str, help="Directorio de output")
    args = parser.parse_args()

    # Coleccionar imágenes
    images = collect_images(OUTPUT_DIR)

    if not images:
        log.error("No hay imágenes para procesar")
        return

    if args.stats:
        show_stats(images)
        return

    if args.splits:
        # Crear splits
        split_data = create_splits(images, seed=args.seed)

        # Guardar splits como JSON
        splits_file = SPLITS_DIR / "splits.json"
        SPLITS_DIR.mkdir(exist_ok=True)

        # Convertir paths a strings para JSON
        for split_name in split_data:
            for img in split_data[split_name]:
                img["path"] = img.pop("path")

        with open(splits_file, "w", encoding="utf-8") as f:
            json.dump(split_data, f, indent=2, ensure_ascii=False)

        log.info(f"Splits guardados: {splits_file}")

        if args.symlinks:
            create_symlinks(split_data, SPLITS_DIR)

    if args.yaml:
        yaml_path = SPLITS_DIR / "dataset.yaml"
        generate_yaml(images, yaml_path)

    if args.kohya_reg:
        reg_dir = generate_kohya_reg_yaml(SPLITS_DIR)
        log.info(f"Kohya reg images: {reg_dir}")

    if not (args.splits or args.yaml or args.kohya_reg or args.stats):
        # Por defecto mostrar stats
        show_stats(images)


if __name__ == "__main__":
    main()
