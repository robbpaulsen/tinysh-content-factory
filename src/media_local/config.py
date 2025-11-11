"""Device configuration and torch setup for local media processing.

Ported from server-code-and-layout/video/config.py
"""

import os

from loguru import logger

# Try to import torch, but make it optional for systems without it
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning(
        "PyTorch not available - TTS features will be disabled. "
        "Install with: uv pip install torch torchaudio"
    )


def detect_device():
    """Detect best available device: CUDA > MPS > CPU."""
    if not TORCH_AVAILABLE:
        return "cpu"

    if torch.cuda.is_available():
        device_obj = torch.device("cuda")
        logger.info(f"Using CUDA device: {torch.cuda.get_device_name(0)}")
        return device_obj
    elif torch.backends.mps.is_available():
        device_obj = torch.device("mps")
        logger.info("Using Apple MPS (Metal Performance Shaders) device")
        return device_obj
    else:
        device_obj = torch.device("cpu")

        # Configure CPU thread count
        num_cores = os.cpu_count()

        # Check cgroups for container limits
        if os.path.exists("/sys/fs/cgroup/cpu.max"):
            try:
                with open("/sys/fs/cgroup/cpu.max", "r") as f:
                    line = f.readline()
                    parts = line.split()
                    if len(parts) == 2 and parts[0] != "max":
                        cpu_max = int(parts[0])
                        cpu_period = int(parts[1])
                        num_cores = cpu_max // cpu_period
                        logger.info(f"Using {num_cores} cores from cgroups")
            except Exception as e:
                logger.warning(f"Error reading cgroups: {e}, using os.cpu_count()")

        logger.info(f"Using CPU device with {num_cores} cores")

        # Set torch thread count
        num_threads = os.environ.get("NUM_THREADS", num_cores)
        torch.set_num_threads(int(num_threads))
        torch.set_num_interop_threads(int(num_threads))
        logger.info(f"PyTorch using {num_threads} threads")

        return device_obj


# Global device instance
device = detect_device() if TORCH_AVAILABLE else "cpu"


def get_device_info() -> dict:
    """Get detailed device information for debugging."""
    info = {
        "torch_available": TORCH_AVAILABLE,
        "device_type": str(device),
    }

    if TORCH_AVAILABLE:
        info.update(
            {
                "cuda_available": torch.cuda.is_available(),
                "mps_available": torch.backends.mps.is_available(),
                "torch_version": torch.__version__,
            }
        )

        if torch.cuda.is_available():
            info.update(
                {
                    "cuda_device_name": torch.cuda.get_device_name(0),
                    "cuda_device_count": torch.cuda.device_count(),
                }
            )

    return info


# Patch torch.load to always use detected device (from original server code)
if TORCH_AVAILABLE:
    map_location = torch.device(device) if isinstance(device, str) else device
    torch_load_original = torch.load

    def patched_torch_load(*args, **kwargs):
        """Patched torch.load that auto-sets map_location."""
        if "map_location" not in kwargs:
            kwargs["map_location"] = map_location
        return torch_load_original(*args, **kwargs)

    torch.load = patched_torch_load
    logger.debug("Patched torch.load with auto map_location")


__all__ = ["device", "get_device_info", "TORCH_AVAILABLE"]
