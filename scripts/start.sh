#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${MODE_TO_RUN:-pod}" == pod ]] || { echo 'Pod mode only' >&2; exit 2; }
volume_root="${RUNPOD_VOLUME_ROOT:-/workspace}"
[[ -d "$volume_root" ]] || { echo "Missing volume: $volume_root" >&2; exit 3; }
mountpoint -q "$volume_root" || { echo "Persistent volume is not mounted at $volume_root" >&2; exit 3; }

if [[ -n "${PUBLIC_KEY:-}" ]]; then
  install -d -m 700 /root/.ssh
  printf '%s\n' "$PUBLIC_KEY" > /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys
  ssh-keygen -A
  service ssh start
fi

project_dir="$volume_root/qwen-image-2.1-bf16"
mkdir -p "$project_dir/logs" "$project_dir/outputs" "$project_dir/input" \
  "$project_dir/temp" "$project_dir/user/default/workflows" "$project_dir/hf-cache"
export HF_HOME="$project_dir/hf-cache"
export HUGGINGFACE_HUB_CACHE="$HF_HOME/hub"

preflight_log="$project_dir/logs/preflight-$(date -u +%Y%m%dT%H%M%SZ).txt"
/opt/qwen-image-21-bf16/scripts/preflight.sh >"$preflight_log" 2>&1 || {
  echo "Preflight failed; inspect $preflight_log" >&2
  tail -n 10 "$preflight_log" >&2 || true
  echo 'SSH remains available for repair.'
  while true; do sleep 60; done
}
echo "Preflight: $preflight_log"

bootstrap_log="$project_dir/logs/bootstrap-$(date -u +%Y%m%dT%H%M%SZ).txt"
if [[ "${QWEN_MODEL_AUTO_DOWNLOAD:-1}" == 1 ]]; then
  /opt/comfyui-venv/bin/python -u /opt/qwen-image-21-bf16/scripts/bootstrap_models.py >"$bootstrap_log" 2>&1 || {
    echo "Model bootstrap failed; inspect $bootstrap_log" >&2
    tail -n 10 "$bootstrap_log" >&2 || true
    echo 'SSH remains available for repair.'
    while true; do sleep 60; done
  }
else
  /opt/comfyui-venv/bin/python -u /opt/qwen-image-21-bf16/scripts/bootstrap_models.py --verify-only >"$bootstrap_log" 2>&1 || {
    echo "Required BF16 models missing; inspect $bootstrap_log" >&2
    while true; do sleep 60; done
  }
fi
echo "Model bootstrap: $bootstrap_log"

for workflow in /opt/qwen-image-21-bf16/workflows/gui/*.json; do
  destination="$project_dir/user/default/workflows/$(basename "$workflow")"
  [[ -e "$destination" ]] || cp "$workflow" "$destination"
done
for asset in /opt/qwen-image-21-bf16/workflows/assets/*.png; do
  destination="$project_dir/input/$(basename "$asset")"
  [[ -e "$destination" ]] || cp "$asset" "$destination"
done

echo 'ComfyUI starting on 0.0.0.0:8188'
exec /opt/comfyui-venv/bin/python -u /opt/ComfyUI-qwen21/main.py \
  --disable-auto-launch --listen 0.0.0.0 --port 8188 \
  --input-directory "$project_dir/input" \
  --output-directory "$project_dir/outputs" \
  --temp-directory "$project_dir/temp" \
  --user-directory "$project_dir/user" \
  --database-url "sqlite:///$project_dir/user/comfyui.db" \
  --extra-model-paths-config /opt/qwen-image-21-bf16/config/extra_model_paths.yaml \
  --cache-classic --disable-pinned-memory
