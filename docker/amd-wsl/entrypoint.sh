#!/bin/bash
set -e

echo '=== Text Generation WebUI AMD WSL2 ==='
echo ''

# Display ROCm GPU information
echo "=== ROCm GPU Information ==="
/opt/rocm/bin/rocminfo | grep -E "Name|Marketing Name" || echo "rocminfo failed"
echo ""

# Display PyTorch information
echo "=== PyTorch Environment ==="
echo -n "PyTorch Import: "
python -c "import torch" 2>/dev/null && echo "Success" || echo "Failure"

echo -n "HIP Available: "
python -c "import torch; print(torch.cuda.is_available())"

echo -n "Device Name [0]: "
python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU')" 2>/dev/null || echo "Error getting device name"

echo ""
echo "=== Full PyTorch Environment ==="
python -m torch.utils.collect_env
echo ""

# Start server directly (no installer needed - PyTorch pre-installed in base image)
exec python server.py --api --listen "$@"
