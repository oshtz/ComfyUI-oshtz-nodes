import io
from inspect import cleandoc
import math
import base64
import requests
import json
import os
import numpy as np
from PIL import Image
import torch

# ComfyUI imports
try:
    from comfy.utils import common_upscale
    from comfy.comfy_types.node_typing import IO, ComfyNodeABC, InputTypeDict
except ImportError:
    class ComfyNodeABC: pass
    class IO:
        STRING = "STRING"
        INT = "INT"
        IMAGE = "IMAGE"
        MASK = "MASK"
        COMBO = "COMBO"
    InputTypeDict = dict
    def common_upscale(samples, width, height, mode, crop): return samples

_MODEL_ID = "gpt-image-1"
_OPENAI_API_BASE_URL = "https://api.openai.com/v1"

def downscale_input(image_tensor):
    samples = image_tensor.unsqueeze(0).movedim(-1, 1)
    H, W = samples.shape[2], samples.shape[3]
    target_total_pixels = int(1536 * 1024)
    current_pixels = W * H
    if current_pixels <= target_total_pixels:
        return image_tensor
    scale_by = math.sqrt(target_total_pixels / current_pixels)
    new_width = round(W * scale_by)
    new_height = round(H * scale_by)
    s = common_upscale(samples, new_width, new_height, "lanczos", "disabled")
    s = s.squeeze(0).movedim(1, -1)
    return s

def prepare_image_for_api(image_tensor):
    scaled_image_tensor = downscale_input(image_tensor.cpu().detach())
    image_np = (scaled_image_tensor.numpy() * 255).clip(0, 255).astype(np.uint8)
    if image_np.shape[-1] == 4:
        img = Image.fromarray(image_np, 'RGBA')
    elif image_np.shape[-1] == 3:
        img = Image.fromarray(image_np, 'RGB')
    else:
        raise ValueError(f"Unsupported number of channels: {image_np.shape[-1]}")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def prepare_mask_for_api(mask_tensor, image_shape_hw):
    if mask_tensor.shape != image_shape_hw:
        mask_for_resize = mask_tensor.unsqueeze(0).unsqueeze(0)
        resized_mask = common_upscale(mask_for_resize, image_shape_hw[1], image_shape_hw[0], "nearest", "disabled")
        mask_tensor = resized_mask.squeeze(0).squeeze(0)
        if mask_tensor.shape != image_shape_hw:
            raise ValueError(f"Mask resize failed. Final shape {mask_tensor.shape} still differs from image {image_shape_hw}.")
    mask_tensor_cpu = mask_tensor.cpu().detach()
    height, width = mask_tensor_cpu.shape
    rgba_mask_np = np.zeros((height, width, 4), dtype=np.float32)
    rgba_mask_np[mask_tensor_cpu > 0.5, 3] = 0.0
    rgba_mask_np[mask_tensor_cpu <= 0.5, 3] = 1.0
    mask_np_uint8 = (rgba_mask_np * 255).clip(0, 255).astype(np.uint8)
    mask_img = Image.fromarray(mask_np_uint8, 'RGBA')
    mask_byte_arr = io.BytesIO()
    mask_img.save(mask_byte_arr, format='PNG')
    mask_byte_arr.seek(0)
    return mask_byte_arr

def process_api_response(response_json):
    if 'data' not in response_json or not response_json['data']:
        error_message = response_json.get('error', {}).get('message', 'Unknown error')
        raise Exception(f"API Error: {error_message}")
    image_tensors = []
    for i, item in enumerate(response_json['data']):
        b64_data = item.get('b64_json')
        image_url = item.get('url')
        img = None
        try:
            if b64_data:
                img_data = base64.b64decode(b64_data)
                img = Image.open(io.BytesIO(img_data))
            elif image_url:
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                img = Image.open(io.BytesIO(img_response.content))
            else:
                continue
            img = img.convert("RGBA")
            img_array = np.array(img).astype(np.float32) / 255.0
            img_tensor = torch.from_numpy(img_array)
            image_tensors.append(img_tensor)
        except Exception as e:
            continue
    if not image_tensors:
        raise Exception("Failed to process any images from the API response")
    return torch.stack(image_tensors, dim=0)

class GPTImage1(ComfyNodeABC):
    """
    Generates images via OpenAI's vision model (specify correct ID in _MODEL_ID).
    Requires a user-provided API key for direct OpenAI API calls only.
    """
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls) -> InputTypeDict:
        return {
            "required": {
                "prompt": (IO.STRING, {"multiline": True, "default": "", "tooltip": f"Text prompt for the {_MODEL_ID} model"}),
                "api_key": (IO.STRING, {"multiline": False, "default": "", "tooltip": "Your OpenAI API Key (required)"}),
            },
            "optional": {
                "seed": (IO.INT, {"default": 0, "min": 0, "max": 2**31-1, "step": 1, "display": "number", "tooltip": "Seed for generation (check model support)"}),
                "quality": (IO.COMBO, {"options": ["low", "medium", "high"], "default": "low", "tooltip": "Image quality, affects cost and generation time."}),
                "background": (IO.COMBO, {"options": ["opaque", "transparent"], "default": "opaque", "tooltip": "Return image with or without background"}),
                "size": (IO.COMBO, {"options": ["auto", "1024x1024", "1024x1536", "1536x1024"], "default": "auto", "tooltip": "Image size"}),
                "n": (IO.INT, {"default": 1, "min": 1, "max": 8, "step": 1, "display": "number", "tooltip": "How many images to generate"}),
                "image": (IO.IMAGE, {"default": None, "tooltip": "Optional reference image for editing (requires 'mask' too)"}),
                "mask": (IO.MASK, {"default": None, "tooltip": "Optional mask for inpainting (requires 'image' too, white=edit area)"}),
            }
        }

    RETURN_TYPES = (IO.IMAGE,)
    FUNCTION = "api_call"
    CATEGORY = "api/OpenAI"
    DESCRIPTION = cleandoc(__doc__ or f"OpenAI {_MODEL_ID} Image (Direct API Key)")
    API_NODE = False

    def api_call(self, prompt, api_key, seed=0, quality="low", background="opaque", size="auto", n=1, image=None, mask=None):
        final_api_key = api_key.strip() or os.environ.get('OPENAI_API_KEY', '').strip()
        if not final_api_key:
            raise ValueError("An OpenAI API key is required. Please provide it as input or set the OPENAI_API_KEY environment variable.")
        headers = {
            "Authorization": f"Bearer {final_api_key}",
        }
        files = {}
        data = {
            "model": _MODEL_ID,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
            "background": background,
            # 'response_format': 'b64_json',  # Removed because it's not supported
        }
        is_edit = image is not None and mask is not None
        if is_edit:
            endpoint = f"{_OPENAI_API_BASE_URL}/images/edits"
            if image.shape[0] != 1 or mask.shape[0] != 1:
                raise ValueError("Image editing currently supports only batch size 1 for image and mask.")
            image_bytes = prepare_image_for_api(image.squeeze(0))
            mask_bytes = prepare_mask_for_api(mask.squeeze(0), image.shape[1:3])
            files['image'] = ('image.png', image_bytes, 'image/png')
            files['mask'] = ('mask.png', mask_bytes, 'image/png')
        elif image is not None or mask is not None:
            raise ValueError("For image editing, both 'image' and 'mask' inputs are required.")
        else:
            endpoint = f"{_OPENAI_API_BASE_URL}/images/generations"
        try:
            if files:
                response = requests.post(endpoint, headers=headers, data=data, files=files, timeout=120)
            else:
                headers["Content-Type"] = "application/json"
                response = requests.post(endpoint, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            response_json = response.json()
        except requests.exceptions.RequestException as e:
            error_detail = ""
            try:
                if e.response is not None:
                    error_detail = e.response.text
            except Exception:
                pass
            raise Exception(f"OpenAI API request failed: {e}\n{error_detail}") from e
        img_tensor_batch = process_api_response(response_json)
        return (img_tensor_batch,)

NODE_CLASS_MAPPINGS = {
    "GPTImage1": GPTImage1,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GPTImage1": "GPT Image 1 (Direct API)",
}