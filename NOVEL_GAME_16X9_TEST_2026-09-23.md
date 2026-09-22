# Qwen-Image-2.1 BF16: 16:9 novel-game material test

Tested on 2026-09-23 with the official `Qwen/Qwen-Image-2.1` checkpoint.
All three images were generated entirely on the GPU in BF16. No negative
prompt, CFG override, quantization, LoRA, CPU offload, or alternate model was
used.

## Configuration

```text
GPU: NVIDIA A100-SXM4-80GB
Model revision: 790c92633540aa0cb11d9abf19eb46d861714758
Resolution: 2752x1536 (16:9)
Steps: 40
Transformer / text encoder / VAE: torch.bfloat16
```

The exact prompts and seeds are stored in
[`scripts/test_novel_game_16x9.py`](scripts/test_novel_game_16x9.py). Run all
three variants inside the Pod with:

```bash
cd /workspace/qwen-image-2.1-bf16
/opt/comfyui-venv/bin/python -u scripts/test_novel_game_16x9.py \
  2>&1 | tee logs/novel-game-16x9.log
```

Use `--only production_refined_ja` to render only the final preset.

## Measurements

| Variant | Seed | Time | Peak allocated | Peak reserved | nvidia-smi peak |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct Japanese prompt | 42 | 81.881s | 56.915GiB | 63.098GiB | 65,555MiB |
| Qwen-oriented composition | 43 | 81.291s | 56.943GiB | 63.092GiB | 65,549MiB |
| Production-refined preset | 44 | 81.814s | 56.984GiB | 63.168GiB | 65,627MiB |

All files decode as RGBA PNG at 2752x1536.

## Visual review

### Direct Japanese prompt

- Strongest flirtatious gesture, face, cat-ear styling, choker, and pink cafe
  atmosphere.
- The framing became a waist-up portrait, so the thighs and bar-stool seat are
  outside the frame.
- A blurred chalkboard-like area contains pseudo-writing.

### Qwen-oriented composition

- Best overall match to the requested framing: head through thighs, seated
  pose, stool, black dress, tail, cafe, and direct eye contact are all visible.
- The face is slightly more game-CG-like than the other two.
- It added a second bell to one cat ear and generated pseudo-writing on cafe
  cards in the background.

### Production-refined preset

- Most photographic face and skin. The head, thighs, stool, dress, choker bell,
  and tail are clearly visible, with useful empty pink wall space for later
  visual-novel layout.
- It correctly removed the extra ear bell.
- It ignored the requested hand-near-cheek pose, and small menu/sign areas with
  pseudo-writing remain at the far left and upper right.

The test shows that Qwen-Image-2.1 can produce a useful photorealistic romance
visual-novel CG from Japanese instructions. The second variant is the closest
single-pass match to the supplied scene description. The third is the better
base when realistic skin, clear thighs/stool, and layout space matter. A final
production pass should remove or replace cafe signs because a text-free prompt
did not reliably suppress pseudo-writing.

## Outputs

Pod directory:

```text
/workspace/qwen-image-2.1-bf16/outputs/novel-game-16x9/
```

Local files:

- `results/jk66m7h6udiqhs/novel-game-16x9/qwen21_novel_game_16x9_direct_ja_seed42.png`
- `results/jk66m7h6udiqhs/novel-game-16x9/qwen21_novel_game_16x9_qwen_refined_ja_seed43.png`
- `results/jk66m7h6udiqhs/novel-game-16x9/qwen21_novel_game_16x9_production_refined_ja_seed44.png`
- `results/jk66m7h6udiqhs/novel-game-16x9/metrics.json`
- `results/jk66m7h6udiqhs/novel-game-16x9/metrics_production_refined_ja.json`

## ComfyUI preset

`qwen21_bf16_novel_game_16x9_40step.json` contains the production-refined
prompt, 2752x1536 resolution, 40 steps, seed 44, CFG 1, and only the three BF16
model files. It is installed in the running Pod's **Workflows** list.
