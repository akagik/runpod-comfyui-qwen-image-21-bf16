#!/usr/bin/env python3
"""Official BF16 Diffusers load, 1024 smoke, 2048 baseline, then image edit."""

import importlib.metadata
import json
import os
import subprocess
import threading
import time
import traceback
from pathlib import Path

import torch
from PIL import Image
from diffusers import QwenImage21Pipeline
from huggingface_hub import snapshot_download

MODEL_ID = "Qwen/Qwen-Image-2.1"
MODEL_REVISION = "790c92633540aa0cb11d9abf19eb46d861714758"
PROMPT = (
    "A cinematic portrait of an adult woman standing in an elegant old European room, "
    "natural skin texture, detailed eyes, realistic hair strands, soft warm window light, "
    "dark wooden wall panels, burgundy velvet furniture in the background, "
    "photorealistic, highly detailed"
)
EDIT_PROMPT = (
    "Change the background to a luxurious nighttime hotel room. "
    "Keep the same adult woman's identity, facial features, hairstyle, "
    "body proportions and camera framing."
)
ROOT = Path(os.environ.get("RUNPOD_VOLUME_ROOT", "/workspace")) / "qwen-image-2.1-bf16"
OUT = ROOT / "outputs" / "diffusers"


def gib(value: int) -> float:
    return round(value / 1024**3, 3)


class SmiSampler:
    def __init__(self):
        self.stop = threading.Event()
        self.max_mib = 0
        self.samples = []
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop.is_set():
            try:
                value = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-i", "0"],
                    text=True, timeout=5,
                ).strip().splitlines()[0]
                mib = int(value)
                self.max_mib = max(self.max_mib, mib)
                self.samples.append([time.time(), mib])
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
            self.stop.wait(0.5)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=6)


def measure(name, action):
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    start = time.perf_counter()
    with SmiSampler() as smi:
        result = action()
        torch.cuda.synchronize()
    data = {
        "seconds": round(time.perf_counter() - start, 3),
        "peak_allocated_gib": gib(torch.cuda.max_memory_allocated()),
        "peak_reserved_gib": gib(torch.cuda.max_memory_reserved()),
        "nvidia_smi_peak_mib": smi.max_mib,
    }
    print(name, json.dumps(data, ensure_ascii=False), flush=True)
    return result, data, smi.samples


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert torch.cuda.is_available(), "CUDA is unavailable"
    assert torch.cuda.is_bf16_supported(), "GPU does not support BF16"
    metrics = {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "gpu": torch.cuda.get_device_name(0),
        "vram_gib": gib(torch.cuda.get_device_properties(0).total_memory),
        "python": os.sys.version.split()[0],
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "transformers": importlib.metadata.version("transformers"),
        "diffusers": importlib.metadata.version("diffusers"),
        "precision": "BF16",
    }
    print(json.dumps(metrics, indent=2), flush=True)
    try:
        download_start = time.perf_counter()
        snapshot_download(
            repo_id=MODEL_ID, revision=MODEL_REVISION,
            cache_dir=ROOT / "hf-cache" / "hub",
        )
        metrics["download_seconds"] = round(time.perf_counter() - download_start, 3)
        pipe, metrics["load"], _ = measure(
            "load",
            lambda: QwenImage21Pipeline.from_pretrained(
                MODEL_ID, revision=MODEL_REVISION, torch_dtype=torch.bfloat16,
                cache_dir=ROOT / "hf-cache" / "hub",
            ).to("cuda"),
        )
        metrics["dtypes"] = {
            "transformer": str(pipe.transformer.dtype),
            "text_encoder": str(next(pipe.text_encoder.parameters()).dtype),
            "vae": str(next(pipe.vae.parameters()).dtype),
        }
        print("Component dtypes:", metrics["dtypes"], flush=True)
        assert pipe.transformer.dtype == torch.bfloat16, "Transformer is not BF16"

        def infer(**kwargs):
            with torch.inference_mode():
                return pipe(**kwargs).images[0]

        smoke, metrics["smoke_1024"], samples = measure(
            "1024 smoke",
            lambda: infer(
                prompt=PROMPT, width=1024, height=1024, num_inference_steps=10,
                generator=torch.Generator(device="cuda").manual_seed(42),
            ),
        )
        smoke.save(OUT / "qwen21_bf16_smoke_1024.png")
        (OUT / "nvidia-smi-smoke.json").write_text(json.dumps(samples))

        baseline, metrics["baseline_2048"], samples = measure(
            "2048 BF16 baseline",
            lambda: infer(
                prompt=PROMPT, width=2048, height=2048, num_inference_steps=40,
                generator=torch.Generator(device="cuda").manual_seed(42),
            ),
        )
        baseline.save(OUT / "qwen21_bf16_2048.png")
        (OUT / "nvidia-smi-baseline.json").write_text(json.dumps(samples))
        metrics["baseline_2048"].update({"width": 2048, "height": 2048, "steps": 40, "seed": 42})

        source = Image.open(OUT / "qwen21_bf16_2048.png").convert("RGB")
        edited, metrics["edit"], samples = measure(
            "image edit",
            lambda: infer(
                prompt=EDIT_PROMPT, image=source, num_inference_steps=40,
                generator=torch.Generator(device="cuda").manual_seed(42),
            ),
        )
        edited.save(OUT / "qwen21_bf16_edit.png")
        (OUT / "nvidia-smi-edit.json").write_text(json.dumps(samples))
        metrics["edit"].update({"width": edited.width, "height": edited.height, "steps": 40, "seed": 42})
        metrics["status"] = "complete"
    except Exception:
        metrics["status"] = "failed"
        metrics["error"] = traceback.format_exc()
        raise
    finally:
        (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False))
        print("Metrics:", OUT / "metrics.json", flush=True)


if __name__ == "__main__":
    main()
