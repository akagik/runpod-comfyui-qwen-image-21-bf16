# Reproduce the Qwen-Image-2.1 full-BF16 Pod

This runbook recreates the environment that successfully ran the official
`Qwen/Qwen-Image-2.1` checkpoint in full BF16 on 2026-09-23.

## Verified reference

| Item | Verified value |
| --- | --- |
| RunPod template | `mzav9rhpen` |
| Current template image | `ghcr.io/akagik/runpod-comfyui-qwen-image-21-bf16:0.1.3@sha256:ec46236609a7e7ecea33904df0a043a1b529d77ad52eb8c7f0b1d1250cdc5e9b` |
| GPU | NVIDIA A100-SXM4-80GB |
| Host CUDA / driver | 13.0 / 580.159.04 |
| Network Volume | `n7h9tqohhb`, EUR-IS-1, mounted at `/workspace` |
| Model | `Qwen/Qwen-Image-2.1` revision `790c92633540aa0cb11d9abf19eb46d861714758` |
| Result | 2048×2048, 40 steps, seed 42 in 78.926 seconds |

The tested GPU has 80GB VRAM. A 48GB card is allowed as an experiment but has
not been proven to hold the 2048 full-GPU BF16 baseline. Do not silently switch
to quantization or CPU offload after an OOM.

## 1. Read-only checks

Before creating a billable resource:

1. Read the live RunPod GPU catalog for the target data center and host CUDA.
2. Confirm the GPU price and present the total hourly cost.
3. Confirm the selected Network Volume is in the same data center and has
   enough free space.
4. Obtain explicit approval for the priced GPU/DC/Volume combination.

Budget at least 70GB of persistent free space when running both paths: the
ComfyUI BF16 repack is about 32.4GB and the separate official Diffusers cache is
roughly another 30GB. A 100GB or larger Volume is recommended.

## 2. Template configuration

The account template `mzav9rhpen` is already configured as follows:

```text
Name: Qwen Image 2.1 Official BF16 ComfyUI + Diffusers 0.1.3 Resident
Container disk: 40GB
Ports: 8188/http, 22/tcp
Allowed host CUDA: 13.0, 13.2
SSH: enabled
Jupyter: disabled
MODE_TO_RUN=pod
RUNPOD_VOLUME_ROOT=/workspace
QWEN_MODEL_AUTO_DOWNLOAD=1
```

For another account, create a private template with the same immutable image,
ports, disk size, environment, and CUDA versions. Select the Network Volume
when deploying the Pod; it is intentionally not embedded in the template.

Image 0.1.2 is a file-only layer over the fully exercised 0.1.1 runtime. It adds
the 16:9 test script and ComfyUI preset. Image 0.1.3 is another thin layer over
the immutable 0.1.2 digest and changes only `scripts/start.sh`: ComfyUI now uses
`--cache-classic` instead of `--cache-none`, allowing loader outputs to survive
between prompts. The linux/amd64 build, shell checks, Python checks, and workflow
verifier passed in GitHub Actions run `35788240585`; CUDA, Python, PyTorch,
Diffusers, ComfyUI, and model files are inherited unchanged.

## 3. Create the Pod

The verified CLI shape is:

```bash
runpodctl pod create \
  --name qwen-image-21-bf16 \
  --template-id mzav9rhpen \
  --gpu-id "NVIDIA A100-SXM4-80GB" \
  --gpu-count 1 \
  --cloud-type SECURE \
  --data-center-ids EUR-IS-1 \
  --network-volume-id n7h9tqohhb \
  --min-cuda-version 13.0 \
  --ssh
```

Choose a different GPU or Volume only after repeating the stock, compatibility,
capacity, and cost checks. Network Volumes are available only to Secure Cloud
Pods and constrain the Pod to the Volume's data center.

## 4. Wait for readiness

Do not create a second Pod while the image is downloading. Inspect the one Pod:

```bash
runpodctl ssh info POD_ID
```

The entrypoint performs these steps:

1. Refuses to continue unless `/workspace` is a real persistent mount.
2. Writes `nvidia-smi`, Python, disk, RAM, Torch, CUDA, and BF16 checks to
   `/workspace/qwen-image-2.1-bf16/logs/preflight-*.txt`.
3. Downloads exactly the three pinned Comfy-Org BF16 files and symlinks them
   into dedicated ComfyUI model directories.
4. Copies the four manual workflows into the user's Workflows directory.
5. Starts ComfyUI on `0.0.0.0:8188`.

Readiness is complete only when both conditions pass:

```bash
curl -fsS "https://POD_ID-8188.proxy.runpod.net/system_stats"

ssh POD_CONNECTION \
  'tail -n 50 /workspace/qwen-image-2.1-bf16/logs/bootstrap-*.txt'
```

The bootstrap log must show all three files as `Ready`:

```text
qwen_image_2.1_bf16.safetensors
qwen3vl_8b_bf16.safetensors
qwen_image_2.1_vae_bf16.safetensors
```

An HTTP 502 while the image or models are loading is expected. It is not ready
until `/system_stats` returns HTTP 200.

## 5. Run the official Diffusers baseline

Connect over SSH and run:

```bash
cd /workspace/qwen-image-2.1-bf16
/opt/comfyui-venv/bin/python -u \
  /opt/qwen-image-21-bf16/scripts/test_qwen21_bf16.py \
  2>&1 | tee logs/diffusers-benchmark.log
```

The success criteria are:

- `QwenImage21Pipeline` loads `Qwen/Qwen-Image-2.1`.
- Transformer, text encoder, and VAE report `torch.bfloat16`.
- The 1024×1024 / 10-step smoke test succeeds.
- The 2048×2048 / 40-step / seed-42 baseline succeeds.
- Image Edit succeeds.
- `metrics.json`, three PNGs, and sampled VRAM data are written below
  `/workspace/qwen-image-2.1-bf16/outputs/diffusers`.

## 6. Use ComfyUI

Open:

```text
https://POD_ID-8188.proxy.runpod.net
```

Select a workflow from **Workflows**:

- `qwen21_bf16_t2i_smoke_1024_10step.json`
- `qwen21_bf16_t2i_2048_40step.json`
- `qwen21_bf16_novel_game_16x9_40step.json`
- `qwen21_bf16_image_edit_40step.json`

All four explicitly reference only the BF16 diffusion model, BF16 text
encoder, and BF16 VAE. The edit workflow includes sample inputs; replace them
with files uploaded through ComfyUI for normal use.

The novel-game workflow uses the tested production-refined Japanese prompt at
2752×1536, 40 steps, seed 44, and CFG 1. Its Diffusers comparison and visual
review are in `NOVEL_GAME_16X9_TEST_2026-09-23.md`.

## 7. Use RunPod Comfy Manager

RunPod Comfy Manager 0.20.4 includes two profiled workflows:

- `qwen-image-2.1-bf16-t2i` v1
- `qwen-image-2.1-bf16-edit` v1

Install the built-ins once, submit a request Markdown, and watch the returned
job ID:

```bash
rcmctl health --json
rcmctl workflow-install-builtins --json
rcmctl workflow qwen-image-2.1-bf16-t2i 1 --json
rcmctl validate /absolute/path/request.md --json
rcmctl submit /absolute/path/request.md --json
rcmctl watch JOB_ID --json
```

Both workflows use model profile `qwen-image-2.1-official-bf16` and the same
loader signature. Manager therefore does not call ComfyUI `/free` when moving
between T2I and Edit. Image 0.1.3 also keeps those loader node outputs in the
ComfyUI classic cache. The first request after a cold Pod start loads the model;
later requests in that Pod process reuse it. Full Markdown examples, multi-image
reference rules, verification commands, and the observed Manager smoke results
are in [RUNPOD_COMFY_MANAGER.md](RUNPOD_COMFY_MANAGER.md).

## 8. Persistence and cleanup

Everything that must survive belongs below
`/workspace/qwen-image-2.1-bf16`. The 40GB container disk is disposable.

The Pod continues GPU billing while running. Stop or terminate it only after an
explicit user instruction:

- **Stop** ends GPU billing but preserves the Network Volume. The container
  disk is not durable across reset/replacement.
- **Terminate** deletes the Pod. The separately managed Network Volume and its
  Qwen cache remain.

Never delete or overwrite unrelated files already present on a shared Volume.
