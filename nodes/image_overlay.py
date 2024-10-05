import sys
from PIL import Image
import numpy as np
import torch
import comfy.utils

class ImageOverlayNode:
    TITLE = "Image Overlay"
    CATEGORY = "oshtz Nodes"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "overlay_images"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_image": ("IMAGE",),
                "overlay_image": ("IMAGE",),
                "position_x": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "position_y": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "alpha": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    def overlay_images(self, base_image, overlay_image, position_x, position_y, alpha):
        # Local conversion functions
        def tensor2pil(image: torch.Tensor) -> Image.Image:
            return Image.fromarray(image.squeeze().permute(1, 2, 0).byte().numpy())

        def pil2tensor(image: Image.Image) -> torch.Tensor:
            return torch.tensor(np.array(image)).permute(2, 0, 1).unsqueeze(0)

        # Convert tensors to PIL Images
        base_pil = tensor2pil(base_image)
        overlay_pil = tensor2pil(overlay_image)

        # Resize overlay to match the base image size if needed
        if overlay_pil.size != base_pil.size:
            overlay_pil = overlay_pil.resize(base_pil.size, Image.ANTIALIAS)

        # Add alpha channel for transparency if not present
        if overlay_pil.mode != 'RGBA':
            overlay_pil = overlay_pil.convert('RGBA')

        # Create a transparent overlay using alpha value
        overlay = Image.new('RGBA', base_pil.size, (0, 0, 0, 0))
        overlay.paste(overlay_pil, (position_x, position_y))
        overlay = Image.blend(Image.new('RGBA', base_pil.size, (0, 0, 0, 0)), overlay, alpha)

        # Composite images
        result = Image.alpha_composite(base_pil.convert('RGBA'), overlay)

        # Convert back to tensor
        return (pil2tensor(result),)

        return (result,)

NODE_CLASS_MAPPINGS = {
    "ImageOverlayNode": ImageOverlayNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageOverlayNode": "Image Overlay"
}