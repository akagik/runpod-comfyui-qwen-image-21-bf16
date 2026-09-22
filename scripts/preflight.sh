#!/usr/bin/env bash
set -Eeuo pipefail

echo '=== nvidia-smi ==='
nvidia-smi
echo '=== Python ==='
python3 --version
echo '=== Disk ==='
df -h
echo '=== RAM ==='
free -h
echo '=== Torch ==='
/opt/comfyui-venv/bin/python - <<'PY'
import torch
print('torch:', torch.__version__)
print('cuda runtime:', torch.version.cuda)
print('cuda available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
    print('BF16 supported:', torch.cuda.is_bf16_supported())
    print('VRAM GB:', torch.cuda.get_device_properties(0).total_memory / 1024**3)
PY

