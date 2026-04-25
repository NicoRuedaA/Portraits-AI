#!/usr/bin/env python3
"""
prepare_lora_dataset.py — Organiza imágenes para entrenamiento LoRA.

Copia imágenes de Retratos/01_RECORTE_FINAL/ a estructura LoRA:
    datasets/monarca_nombre/
        nombre_1.jpg
        nombre_2.jpg
        ...
"""

import os
import shutil
from pathlib import Path

SRC = Path("Retratos/01_RECORTE_FINAL")
DST = Path("datasets/lora")


def get_monarch_name(filename):
    """Extrae nombre del monarca del nombre de archivo."""
    # Ejemplo: "Felipe II de España 1556-1598_1.jpg" -> "Felipe II de España"
    name = filename.replace(".jpg", "").replace(".png", "").replace(".jpeg", "")

    # Quitar sufijos _1, _2, etc
    parts = name.split()
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    if parts and parts[-1].isdigit():
        parts = parts[:-1]

    # Limpiar años y guiones del final
    clean_parts = []
    for p in parts:
        if (
            p.replace("-", "")
            .replace("_", "")
            .replace("(", "")
            .replace(")", "")
            .isdigit()
        ):
            continue
        clean_parts.append(p)

    return " ".join(clean_parts) if clean_parts else "unknown"


def prepare_dataset():
    """Organiza dataset para LoRA."""
    if not SRC.exists():
        print(f"ERROR: {SRC} no existe")
        print("Primero ejecutar: python main.py --download && python main.py --process")
        return

    # Crear directorio destino
    DST.mkdir(parents=True, exist_ok=True)

    # Agrupar por monarca
    by_monarch = {}

    for img in SRC.rglob("*"):
        if img.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            name = get_monarch_name(img.name)
            if name not in by_monarch:
                by_monarch[name] = []
            by_monarch[name].append(img)

    print(
        f"Encotrados {sum(len(v) for v in by_monarch.values())} imágenes de {len(by_monarch)} monarcas"
    )

    # Copiar
    copied = 0
    for monarch, images in by_monarch.items():
        # Crear carpeta por monarca
        safe_name = "".join(c for c in monarch if c.isalnum() or c in " -").strip()
        target_dir = DST / safe_name
        target_dir.mkdir(exist_ok=True)

        for i, src in enumerate(images, 1):
            ext = src.suffix
            dst_file = target_dir / f"{safe_name}_{i}{ext}"
            shutil.copy2(src, dst_file)
            copied += 1

    print(f"\n✓ Dataset preparado en {DST}/")
    print(f"  {copied} imágenes copiadas")

    # Mostrar estructura
    print("\nEstructura:")
    for d in sorted(DST.iterdir()):
        if d.is_dir():
            count = len(list(d.glob("*")))

            print(f"  {d.name}/ ({count} imgs)")


if __name__ == "__main__":
    prepare_dataset()
