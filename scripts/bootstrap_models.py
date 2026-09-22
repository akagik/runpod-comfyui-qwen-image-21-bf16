#!/usr/bin/env python3
"""Download only Comfy-Org's three official Qwen-Image-2.1 BF16 files."""

import argparse
import os
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO = "Comfy-Org/Qwen-Image-2.1"
REVISION = "ace0edeb3791a594ddfa36ed5f41a178a394e921"
FILES = {
    "diffusion_models/qwen_image_2.1_bf16.safetensors": 14_230_280_616,
    "text_encoders/qwen3vl_8b_bf16.safetensors": 17_534_334_616,
    "vae/qwen_image_2.1_vae_bf16.safetensors": 675_509_688,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = Path(os.environ.get("RUNPOD_VOLUME_ROOT", "/workspace")) / "qwen-image-2.1-bf16"
    cache = root / "hf-cache" / "hub"
    model_dir = root / "comfy-models"

    for relative, size in FILES.items():
        dest = model_dir / relative
        if args.verify_only:
            assert dest.is_file(), f"Missing: {dest}"
            assert dest.stat().st_size == size, f"Incorrect size: {dest}"
            print(f"OK {dest} ({size} bytes)", flush=True)
            continue

        source = Path(hf_hub_download(
            repo_id=REPO, filename=relative, revision=REVISION, cache_dir=cache
        ))
        assert source.stat().st_size == size, f"Unexpected Hub file size: {source}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink():
            assert dest.resolve() == source.resolve(), f"Different existing link: {dest}"
        elif dest.exists():
            raise RuntimeError(f"Existing file is not managed by this installer: {dest}")
        else:
            dest.symlink_to(source)
        print(f"Ready {dest} -> {source} ({size} bytes)", flush=True)


if __name__ == "__main__":
    main()
