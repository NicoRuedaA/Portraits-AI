#!/usr/bin/env python3
"""
train_lora.py — Entrena LoRA para portraits históricos.

Uso:
    python python/train_lora.py --config <config_file>

Config por defecto optimizada para RTX 4060 8GB.
"""

import argparse
import subprocess
import os
from pathlib import Path

# Paths
PROJECT_DIR = Path(__file__).parent.parent
DATASET_DIR = PROJECT_DIR / "datasets" / "lora"
OUTPUT_DIR = PROJECT_DIR / "lora_outputs"
COMFYUI_DIR = Path(os.path.expanduser("F:/Documentos/ComfyUI"))

# Model paths
MODEL_PATH = COMFYUI_DIR / "models" / "v1-5-pruned-emaonly"

DEFAULT_CONFIG = """
# Kohya config optimizada para RTX 4060 8GB
[general]
output_dir = {output_dir}
output_name = portraits_lora
 dataset_config = {{dataset_dir}}/dataset.yaml

[model]
base_model = {model_path}
training_mode = loar

[params]
network_module = networks.lora
network_dim = 64
network_alpha = 64
conv_module = networks.lora
conv_dim = 64
conv_alpha = 64

max_resolution = 768,768
min_resolution = 512,512
train_batch_size = 1
gradient_accumulation_steps = 2
mixed_precision = fp16
save_precision = fp16
lr = 1e-4
lr_scheduler = constant
lr_warmup_steps = 100
max_train_steps = 500
save_every_n_steps = 100
optimizer = adamw8bit
clip_skip = 2
max_token_length = 225

[logging]
log_every_n_steps = 50
logging_dir = {output_dir}/logs
""".strip()


def create_dataset_yaml():
    """Crea dataset.yaml para Kohya."""
    if not DATASET_DIR.exists():
        print(f"ERROR: {DATASET_DIR} no existe")
        print("Primero ejecutar: python python/prepare_lora_dataset.py")
        return False

    # Contar imágenes
    classes = {}
    for d in DATASET_DIR.iterdir():
        if d.is_dir():
            imgs = list(d.glob("*"))
            classes[d.name] = [f"../{d.name}/{i.name}" for i in imgs]

    yaml_content = """# LoRA Dataset config
# ==================
# Estructura: class_name: [paths...]
"""
    for cls, imgs in sorted(classes.items()):
        yaml_content += f"\n{cls}:\n"
        yaml_content += f"  num_repeats: {len(imgs)}\n"
        yaml_content += f'  class_names: ["{cls}"]\n'
        yaml_content += f'  image_dir: "{DATASET_DIR.name}/{cls}"\n'
        yaml_content += f"  num_imgs: {len(imgs)}\n"

    # Kohya usa estructura diferente, crear json
    import json

    dataset_json = {
        "datasets": [
            {
                "class_name": cls,
                "num_repeats": len(imgs),
                "is_local": True,
                "image_path": str(DATASET_DIR / cls),
                "num_images": len(imgs),
                "cache_latents": True,
            }
            for cls, imgs in classes.items()
        ]
    }

    yaml_path = DATASET_DIR / "dataset.json"
    with open(yaml_path, "w", encoding="utf-8") as f:
        json.dump(dataset_json, f, indent=2)

    print(f"✓ Dataset config: {yaml_path}")
    print(f"  {len(classes)} clases, {sum(len(v) for v in classes.values())} imágenes")
    return True


def install_kohya():
    """Instala Kohya si no está."""
    try:
        import kohya

        print("✓ Kohya ya instalado")
        return True
    except ImportError:
        print("📦 Instalando kohya-ng...")
        subprocess.run(["pip", "install", "kohya-ng", "accelerate"], check=True)
        return True


def run_training(config_file: str = None):
    """Ejecuta entrenamiento."""
    # Verificar dataset
    if not create_dataset_yaml():
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Verificar modelo
    if not MODEL_PATH.exists():
        print(f"ERROR: Modelo no encontrado en {MODEL_PATH}")
        print(f"Mové el modelo a: {MODEL_PATH}")
        return

    print("\n" + "=" * 50)
    print("🎨 INICIANDO ENTRENAMIENTO LOA")
    print("=" * 50)
    print(f"Dataset: {DATASET_DIR}")
    print(f"Modelo: {MODEL_PATH}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"VRAM: ~6-7GB (optimizado para 8GB)")
    print("=" * 50 + "\n")

    # Por ahora, mostrar comando para Colab (más estable para 8GB)
    print("""
⚠️  IMPORTANTE: Para RTX 4060 8GB, RECOMENDAMOS COLAB:

1. Subí datasets/lora/ a Google Drive
2. Ejecutá en Colab:
   https://github.com/kohya-ss/sd-scripts/blob/master/sd_scripts/train_network.ipynb

Config óptima ya configurada en el notebook.

Si igual querés intentar local, continuá con...
    """)

    # Intentar local si el usuario quiere
    response = input("\n¿Entrenar LOCALMENTE? (s/N): ").strip().lower()
    if response != "s":
        print("\n✅ Listo. Cuando quieras entrenar:")
        print("   1. python python/prepare_lora_dataset.py")
        print("   2. Subir datasets/lora/ a Google Drive")
        print("   3. Ejecutar Kohya Colab")
        return

    # Entrenamiento local
    print("\n🚀 Iniciando entrenamiento local...")

    cmd = [
        "python",
        "-m",
        "kohya",
        "train",
        "--dataset_config",
        str(DATASET_DIR / "dataset.json"),
        "--model",
        str(MODEL_PATH),
        "--output_dir",
        str(OUTPUT_DIR),
        "--output_name",
        "portraits_lora",
        "--network_dim",
        "64",
        "--train_batch_size",
        "1",
        "--resolution",
        "768",
        "--max_train_steps",
        "300",
        "--mixed_precision",
        "fp16",
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print("\n💡 Recomendamos usar Colab para mejor resultado")
    except FileNotFoundError:
        print("❌ Kohya no instalado")
        print("   pip install kohya-ng accelerate")
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Entrena LoRA para portraits")
    parser.add_argument("--config", type=str, help="Config file (opcional)")
    args = parser.parse_args()

    run_training(args.config)
