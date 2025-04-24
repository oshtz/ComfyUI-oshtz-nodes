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


# --- Utilities for Dynamic/Flexible Nodes ---

class AnyType(str):
  """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

  def __ne__(self, __value: object) -> bool:
    return False

class FlexibleOptionalInputType(dict):
  """A special class to make flexible nodes that pass data to our python handlers.

  Enables both flexible/dynamic input types (like for Any Switch) or a dynamic number of inputs
  (like for Any Switch, Context Switch, Context Merge, Power Lora Loader, etc).

  Note, for ComfyUI, all that's needed is the `__contains__` override below, which tells ComfyUI
  that our node will handle the input, regardless of what it is.

  However, with https://github.com/comfyanonymous/ComfyUI/pull/2666 a large change would occur
  requiring more details on the input itself. There, we need to return a list/tuple where the first
  item is the type. This can be a real type, or use the AnyType for additional flexibility.

  This should be forwards compatible unless more changes occur in the PR.
  """
  def __init__(self, type):
    self.type = type

  def __getitem__(self, key):
    return (self.type, )

  def __contains__(self, key):
    return True

# Global instance for convenience
any_type = AnyType("*")
