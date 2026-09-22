# syntax=docker/dockerfile:1.7
# Model-free Qwen-Image-2.1 BF16 Pod image. The parent supplies a tested
# CUDA 13.0 / PyTorch 2.13 / Python 3.12 runtime and SSH support.
ARG BASE_IMAGE=ghcr.io/akagik/runpod-comfyui-minimax-h3:0.1.4@sha256:09e695790b1eb815a92c382f384313712c621172e031dd2cf136a0a7a9ea053e
FROM ${BASE_IMAGE}

ARG COMFYUI_COMMIT=b33e2b55cae074eca5aec96283cceac19aa249ba
ARG DIFFUSERS_COMMIT=fbf49e7f35857f76bc57b177e26f12b03687c668
ARG IMAGE_VERSION=0.1.0

LABEL org.opencontainers.image.title="Qwen Image 2.1 official BF16 on RunPod" \
      org.opencontainers.image.source="https://github.com/akagik/runpod-comfyui-qwen-image-21-bf16" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      io.runpod.qwen.model="Qwen/Qwen-Image-2.1" \
      io.runpod.qwen.precision="bf16" \
      io.runpod.comfyui.commit="${COMFYUI_COMMIT}" \
      io.runpod.diffusers.commit="${DIFFUSERS_COMMIT}"

ENV MODE_TO_RUN=pod \
    RUNPOD_VOLUME_ROOT=/workspace \
    QWEN_MODEL_AUTO_DOWNLOAD=1 \
    COMFYUI_DIR=/opt/ComfyUI-qwen21 \
    QWEN_APP_DIR=/opt/qwen-image-21-bf16 \
    HF_HOME=/workspace/qwen-image-2.1-bf16/hf-cache \
    HUGGINGFACE_HUB_CACHE=/workspace/qwen-image-2.1-bf16/hf-cache/hub \
    PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN git init "${COMFYUI_DIR}" \
    && git -C "${COMFYUI_DIR}" remote add origin https://github.com/Comfy-Org/ComfyUI.git \
    && git -C "${COMFYUI_DIR}" fetch --depth 1 origin "${COMFYUI_COMMIT}" \
    && git -C "${COMFYUI_DIR}" checkout --detach FETCH_HEAD \
    && test "$(git -C "${COMFYUI_DIR}" rev-parse HEAD)" = "${COMFYUI_COMMIT}" \
    && rm -rf "${COMFYUI_DIR}/.git"

# Keep the parent's working torch/CUDA combination. Pip sees torch 2.13.0
# already installed in this image; no explicit torch install or downgrade.
RUN /opt/comfyui-venv/bin/python -m pip install --no-cache-dir \
      -r "${COMFYUI_DIR}/requirements.txt" \
      'transformers>=5.17' accelerate pillow huggingface_hub safetensors sentencepiece \
    && /opt/comfyui-venv/bin/python -m pip install --no-cache-dir \
      "git+https://github.com/huggingface/diffusers.git@${DIFFUSERS_COMMIT}" \
    && /opt/comfyui-venv/bin/python -m pip check \
    && /opt/comfyui-venv/bin/python -c 'import torch; from diffusers import QwenImage21Pipeline; print("torch", torch.__version__, "diffusers QwenImage21Pipeline OK")'

COPY config/ "${QWEN_APP_DIR}/config/"
COPY scripts/ "${QWEN_APP_DIR}/scripts/"
COPY workflows/ "${QWEN_APP_DIR}/workflows/"
COPY README.md "${QWEN_APP_DIR}/README.md"

RUN chmod +x "${QWEN_APP_DIR}/scripts/"*.sh \
    && /opt/comfyui-venv/bin/python -m compileall -q "${QWEN_APP_DIR}/scripts" \
    && bash -n "${QWEN_APP_DIR}/scripts/"*.sh \
    && cd "${COMFYUI_DIR}" \
    && timeout 300 /opt/comfyui-venv/bin/python main.py --quick-test-for-ci --cpu \
      --extra-model-paths-config "${QWEN_APP_DIR}/config/extra_model_paths.yaml"

EXPOSE 8188 22
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8188/system_stats >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/qwen-image-21-bf16/scripts/start.sh"]
CMD []

