import torch
from PIL import Image
import base64
import io
import importlib.util
import sys

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
    return Image.fromarray(image.squeeze().permute(1, 2, 0).byte().numpy())

def pil2base64(image: Image.Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
