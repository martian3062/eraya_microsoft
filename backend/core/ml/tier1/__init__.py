"""
Tier 1 ML — heavy models (PyTorch + PyG + Stable-Baselines3).

GPU policy for RTX 4050 Laptop (6GB VRAM):
  - Hard cap at 4 GB VRAM (fraction = 4/6 ≈ 0.667)
  - DDR5 RAM cap: 8 GB (enforced via PYTORCH_CPU_ALLOCATOR_CONF)
  - CUDA stream per agent to avoid contention between archetypes
"""
import logging
import os

logger = logging.getLogger("eraya.ml.tier1")

TORCH_AVAILABLE = False
PYG_AVAILABLE = False
SB3_AVAILABLE = False
DEVICE = "cpu"

try:
    import torch

    TORCH_AVAILABLE = True

    if torch.cuda.is_available():
        gpu_props = torch.cuda.get_device_properties(0)
        total_vram_gb = gpu_props.total_memory / (1024 ** 3)

        # Hard cap: use at most 4 GB out of available VRAM
        limit_gb = float(os.environ.get("GPU_MEMORY_LIMIT_GB", "4"))
        fraction = min(1.0, limit_gb / total_vram_gb)
        torch.cuda.set_per_process_memory_fraction(fraction, device=0)

        DEVICE = "cuda"
        logger.info(
            "GPU: %s | VRAM: %.1f GB | Limit: %.1f GB (fraction=%.2f) | CUDA %s",
            gpu_props.name,
            total_vram_gb,
            limit_gb,
            fraction,
            torch.version.cuda,
        )
    else:
        logger.info("PyTorch %s available — no CUDA GPU found, using CPU", torch.__version__)

except ImportError:
    TORCH_AVAILABLE = False
    logger.info("PyTorch not installed — tier 1 disabled (run: pip install torch --index-url https://download.pytorch.org/whl/cu128)")

try:
    import torch_geometric  # noqa: F401
    PYG_AVAILABLE = True
except ImportError:
    PYG_AVAILABLE = False

try:
    import stable_baselines3  # noqa: F401
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


def get_device() -> str:
    """Returns 'cuda' or 'cpu' based on what's available and configured."""
    return DEVICE


def tensor_to_device(tensor):
    """Move a tensor to the configured device."""
    if TORCH_AVAILABLE:
        import torch  # noqa: F811
        return tensor.to(DEVICE)
    return tensor


__all__ = ["TORCH_AVAILABLE", "PYG_AVAILABLE", "SB3_AVAILABLE", "DEVICE", "get_device", "tensor_to_device"]
