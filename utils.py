import torch
from PIL import Image
import base64
import io
import importlib.util
import sys
import numpy as np # Added numpy import

def ensure_package(package_name, version=None):
    try:
        if version:
            importlib.import_module(f"{package_name}=={version}")
        else:
            importlib.import_module(package_name)
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package_name}{f'=={version}' if version else ''}"])

def tensor2pil(image: torch.Tensor) -> Image.Image:
    # Assuming input is BHWC (Batch, Height, Width, Channels)
    # Squeeze batch dim, move to CPU, convert to numpy
    img_np = image.squeeze(0).cpu().numpy() # Shape (H, W, C)
    # Convert float [0,1] to uint8 [0,255] if necessary
    if img_np.dtype == np.float32 or img_np.dtype == np.float64:
        img_np = np.clip(img_np * 255, 0, 255).astype(np.uint8)
    elif img_np.dtype != np.uint8:
        # Raise error for unexpected types instead of relying on .byte()
        raise TypeError(f"tensor2pil cannot handle numpy dtype: {img_np.dtype}")

    # Handle grayscale images (H, W, 1) -> (H, W) for PIL
    if img_np.ndim == 3 and img_np.shape[2] == 1:
        img_np = np.squeeze(img_np, axis=2)

    return Image.fromarray(img_np)

def pil2base64(image: Image.Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
