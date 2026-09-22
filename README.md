# Qwen-Image-2.1 official BF16 on RunPod

This Pod image keeps the [official Qwen/Qwen-Image-2.1](https://huggingface.co/Qwen/Qwen-Image-2.1)
Diffusers checkpoint and the [Comfy-Org BF16 repack](https://huggingface.co/Comfy-Org/Qwen-Image-2.1)
separate. It contains no model weights, quantization, LoRA, or custom ComfyUI nodes.

## Pinned inputs

- Base runtime: `ghcr.io/akagik/runpod-comfyui-minimax-h3:0.1.4@sha256:09e695790b1eb815a92c382f384313712c621172e031dd2cf136a0a7a9ea053e` (CUDA 13.0, PyTorch 2.13.0, Python 3.12).
- ComfyUI: `b33e2b55cae074eca5aec96283cceac19aa249ba`.
- Diffusers main: `fbf49e7f35857f76bc57b177e26f12b03687c668`.
- Official Diffusers model: `Qwen/Qwen-Image-2.1` revision `790c92633540aa0cb11d9abf19eb46d861714758`.
- Comfy-Org BF16 model: `Comfy-Org/Qwen-Image-2.1` revision `ace0edeb3791a594ddfa36ed5f41a178a394e921`. Only the diffusion model (14,230,280,616 bytes), text encoder (17,534,334,616 bytes), and VAE (675,509,688 bytes) are downloaded.
- GUI graphs derive from [Comfy-Org/workflow_templates](https://github.com/Comfy-Org/workflow_templates) commit `7ce126c4ec77f44cc7a60f93eec52a197efb9ce5`. The upstream defaults select INT8 ConvRot, so the three bundled copies explicitly select BF16. The included edit sample images are from the same repository.

## Pod template

Template: `mzav9rhpen` (`Qwen Image 2.1 Official BF16 ComfyUI + Diffusers 0.1.2`).
Image: `ghcr.io/akagik/runpod-comfyui-qwen-image-21-bf16:0.1.2@sha256:06ccef7c0797b550a3fbb1809adc7648a39c6188890bcd22d41c208231558c7a`.
`Dockerfile` builds the full 0.1.0 image; `Dockerfile.patch` pins that verified digest
and adds the 0.1.1 persistent-volume guard without reinstalling dependencies.
`Dockerfile.novel` pins the verified 0.1.1 image and adds only the tested 16:9
script and ComfyUI preset. It does not change the CUDA, Python, PyTorch,
Diffusers, ComfyUI, or model bootstrap layers.
Container disk: 40 GB. Ports: `8188/http`, `22/tcp`. Persistent network volume mount: `/workspace`.
Environment: `MODE_TO_RUN=pod`, `RUNPOD_VOLUME_ROOT=/workspace`, `QWEN_MODEL_AUTO_DOWNLOAD=1`.
Allowed host CUDA versions: 13.0 and 13.2. The full baseline was verified on an
A100 SXM 80GB; use a BF16-capable GPU with sufficient VRAM.

For the complete stock check, priced deployment, readiness, benchmark, ComfyUI,
and persistence procedure, read [REPRODUCE.md](REPRODUCE.md).

The entrypoint starts SSH, records `nvidia-smi`, Python, disk, RAM, and torch/CUDA in
`/workspace/qwen-image-2.1-bf16/logs/`, downloads only the three Comfy-Org BF16 files
into a dedicated directory, then starts ComfyUI on port 8188. The persistent Hugging Face
cache is `/workspace/qwen-image-2.1-bf16/hf-cache`. Existing models and workflows elsewhere
on the volume are never overwritten. Restarting a Pod reuses the cache.

## Manual ComfyUI workflows

Open the Pod's ComfyUI proxy URL, then select one of these from **Workflows**:

1. `qwen21_bf16_t2i_smoke_1024_10step.json` — 1024 square, 10 steps, seed 42.
2. `qwen21_bf16_t2i_2048_40step.json` — 2048 square, 40 steps, seed 42, CFG 1.
3. `qwen21_bf16_novel_game_16x9_40step.json` — 2752×1536, 40 steps, seed 44, with the tested Japanese cat-cafe visual-novel prompt.
4. `qwen21_bf16_image_edit_40step.json` — 40-step two-image edit with bundled sample inputs; replace the Load Image selections to use your own files.

All three use only `qwen_image_2.1_bf16.safetensors`, `qwen3vl_8b_bf16.safetensors`,
and `qwen_image_2.1_vae_bf16.safetensors`. The edit workflow's examples load into
`/workspace/qwen-image-2.1-bf16/input`. ComfyUI outputs persist in
`/workspace/qwen-image-2.1-bf16/outputs`.

## Official Diffusers baseline

After `scripts/preflight.sh` confirms CUDA and BF16, run inside the Pod:

```bash
cd /workspace/qwen-image-2.1-bf16
/opt/comfyui-venv/bin/python -u /opt/qwen-image-21-bf16/scripts/test_qwen21_bf16.py \
  2>&1 | tee logs/diffusers-benchmark.log
```

The script downloads the **official** Diffusers checkpoint to the same persistent cache,
loads every component on the GPU in BF16, checks the transformer dtype, generates a
1024/10-step smoke image and a 2048/40-step seed-42 baseline image, then edits the
baseline. It records wall time, PyTorch allocated/reserved peaks, sampled `nvidia-smi`
memory, environment versions, and full errors in `outputs/diffusers/metrics.json`.
No CFG, negative prompt, quantization, CPU offload, or reduced-step adapter is used.

Outputs are `outputs/diffusers/qwen21_bf16_smoke_1024.png`,
`outputs/diffusers/qwen21_bf16_2048.png`, and
`outputs/diffusers/qwen21_bf16_edit.png`.

The verified A100 SXM 80GB result for 2048×2048 / 40 steps / seed 42 was
78.926 seconds with 56.511 GiB peak allocated and 63.771 GiB peak reserved
PyTorch memory. No quantization or CPU offload was used.

The separate [16:9 novel-game test report](NOVEL_GAME_16X9_TEST_2026-09-23.md)
contains three 2752×1536 / 40-step Japanese prompt variants, their timings and
VRAM peaks, a visual review, and the matching ComfyUI preset.
