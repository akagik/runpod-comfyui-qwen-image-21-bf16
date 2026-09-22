#!/usr/bin/env python3
"""Check the official-template derivatives use only BF16 model files."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "workflows" / "gui"
CASES = {
    "qwen21_bf16_t2i_smoke_1024_10step.json": (459, 10, 42),
    "qwen21_bf16_t2i_2048_40step.json": (459, 40, 42),
    "qwen21_bf16_novel_game_16x9_40step.json": (459, 40, 44),
    "qwen21_bf16_image_edit_40step.json": (459, 40, 42),
}
MODELS = {
    "qwen_image_2.1_bf16.safetensors",
    "qwen3vl_8b_bf16.safetensors",
    "qwen_image_2.1_vae_bf16.safetensors",
}

for name, (node_id, steps, seed) in CASES.items():
    data = json.loads((ROOT / name).read_text())
    text = json.dumps(data).lower()
    for forbidden in ("fp8", "int8", "gguf", "convrot", "w4a8", "lora"):
        assert forbidden not in text, (name, forbidden)
    node = next(n for n in data["nodes"] if n["id"] == node_id)
    widgets = node["widgets_values"]
    assert MODELS.issubset(set(widgets)), name
    if "edit" in name:
        assert widgets[3] == 1 and widgets[4] == steps and widgets[10] == seed
    else:
        assert widgets[2] == 1 and widgets[3] == steps and widgets[8] == seed
    if "novel_game_16x9" in name:
        assert widgets[4:6] == [2752, 1536]
        selector = next(n for n in data["nodes"] if n["id"] == 13)
        assert selector["widgets_values"][:2] == ["16:9 (Landscape)", 4]
    if "2048" in name:
        assert widgets[4:6] == [2048, 2048]
        selector = next(n for n in data["nodes"] if n["id"] == 13)
        assert selector["widgets_values"][1] == 4
    print("OK", name)
