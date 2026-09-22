# RunPod Comfy Manager integration

This guide operates Qwen-Image-2.1 official BF16 through RunPod Comfy Manager.
A human writes one Markdown request, Manager uploads references, selects the
running compatible Pod, submits the ComfyUI graph, tracks it, downloads the PNG,
and shows it in the Manager library.

## Fixed components

```text
Manager: RunPod Comfy Manager 0.20.4 or newer
Template: mzav9rhpen
Image: ghcr.io/akagik/runpod-comfyui-qwen-image-21-bf16:0.1.3@sha256:ec46236609a7e7ecea33904df0a043a1b529d77ad52eb8c7f0b1d1250cdc5e9b
Model profile: qwen-image-2.1-official-bf16
T2I workflow: qwen-image-2.1-bf16-t2i v1
Edit workflow: qwen-image-2.1-bf16-edit v1
```

The two workflows load only these files:

```text
qwen_image_2.1_bf16.safetensors
qwen3vl_8b_bf16.safetensors
qwen_image_2.1_vae_bf16.safetensors
```

They use no quantization, LoRA, CPU offload, Lightning, Turbo, or distilled
adapter.

## One-time Manager setup

Start the desktop app and confirm that the Pod is RUNNING and ComfyUI is READY:

```bash
rcmctl health --json
rcmctl pods --json
rcmctl workflow-install-builtins --json
rcmctl workflow qwen-image-2.1-bf16-t2i 1 --json
rcmctl workflow qwen-image-2.1-bf16-edit 1 --json
```

The two workflow reads are the source of truth for Markdown `values` keys.

## T2I Markdown

````markdown
---
formatVersion: 1
workflowId: qwen-image-2.1-bf16-t2i
workflowVersion: 1
outputRoot: ./outputs
preferredPodId: YOUR_POD_ID
values:
  width: 1536
  height: 864
  seed: 42
  steps: 40
  cfg: 1
---
# Scene title

## プロンプト

```text
Photorealistic visual novel character portrait of an adult Japanese woman.
No text, no logo, no watermark, no UI.
```
````

## Image Edit and multi-image reference Markdown

`referenceImages` accepts 1 to 10 local paths. Their order maps directly to
`<image1>` through `<image10>`:

- image 1: edit target
- image 2 and later: character, clothing, background, pose, or composition
  references

````markdown
---
formatVersion: 1
workflowId: qwen-image-2.1-bf16-edit
workflowVersion: 1
outputRoot: ./outputs
preferredPodId: YOUR_POD_ID
values:
  referenceImages:
    - ./character.png
    - ./background.png
    - ./pose.png
  resolution: 1024
  seed: 42
  steps: 40
  cfg: 1
---
# Character, background, and pose composition

## プロンプト

```text
Keep the identity, face, hairstyle, and outfit of the adult character in
<image1>. Place her in the environment from <image2>. Follow the body pose and
camera framing from <image3>. Preserve a realistic photographic style. No text,
logo, watermark, or UI.
```
````

Use one reference for ordinary text-guided editing. Use two references for
character plus background or character plus pose. The output canvas follows
image 1; `resolution` is the total pixel budget.

## Validate, submit, and watch

```bash
rcmctl validate /absolute/path/request.md --json
rcmctl markdown-preview \
  --source-path /absolute/path/request.md \
  --output-root /absolute/path/outputs \
  --preferred-pod-id YOUR_POD_ID \
  --json
rcmctl markdown-submit \
  --source-path /absolute/path/request.md \
  --output-root /absolute/path/outputs \
  --preferred-pod-id YOUR_POD_ID \
  --json
rcmctl watch JOB_ID --json
```

Submit only after validation returns `valid: true` and preview shows the intended
prompt, values, reference order, workflow, Pod, and output path.

## Model residence

The T2I and Edit definitions deliberately use the same node IDs, model loader
settings, and `modelProfile`. Manager records one concrete model signature per
Pod. After the first successful submission, a same-signature job produces
`MODEL_PROFILE_ACTIVE` without `MODEL_PROFILE_CACHE_RELEASE_REQUESTED`.

Image 0.1.3 starts ComfyUI with `--cache-classic`. Loader outputs therefore stay
cached between prompts. The first job after a cold Pod start pays the BF16 model
load; subsequent T2I/Edit requests reuse the cached loaders. Switching to a
different model signature waits for an empty remote queue and then calls
ComfyUI `/free` once. Restarting the Manager app currently loses its in-memory
signature record, so the first profiled job after a Manager restart also performs
one conservative `/free`; following Qwen jobs reuse the signature again.

Check one job's event history with:

```bash
rcmctl events JOB_ID --json
```

Do not run Qwen jobs through standalone one-shot Diffusers scripts for routine
Manager use. Those Python processes necessarily release the model when they
exit.

## Verified Manager smoke run

On 2026-09-23, Manager 0.20.4 submitted both workflows to Pod
`jk66m7h6udiqhs` and downloaded both PNGs:

| Workflow | Job ID | Result |
| --- | --- | --- |
| T2I 1024×1024 / 10 steps | `01a0cb09-81b7-7f71-aca4-2779e933a5dc` | COMPLETED, 1024×1024 RGBA PNG |
| Edit / one reference / 10 steps | `01a0cb0b-9c91-7003-bbbc-8f8f5fbf684f` | COMPLETED, 1376×768 RGBA PNG |

The first job requested a cache release because Manager had just restarted and
the previous signature was unknown. The second job had
`MODEL_PROFILE_ACTIVE` and no cache-release event, proving the T2I-to-Edit
transition stays on the resident profile. The tested live Pod was created from
image 0.1.1 and still used `--cache-none`; template 0.1.3 fixes that ComfyUI
cache setting for newly created Pods. Updating the template does not modify an
already running Pod.

Test requests and downloaded outputs are under `manager-tests/` in the local
workspace. The PNGs also appear in the Manager library.

## Pod lifecycle

The template is a creation snapshot. Starting an existing old Pod does not make
it adopt a newer template image. To use resident image 0.1.3, create the next Pod
from template `mzav9rhpen` and attach a Network Volume in the same data center.
The persistent `/workspace/qwen-image-2.1-bf16` cache avoids downloading the
models again when that Volume is reused.

Manager can route Markdown to a running compatible Pod. It does not start a
manually created stopped Pod. Stop or terminate a Pod only through the approved
operational path; keep the Network Volume when its cached models and outputs are
still needed.
