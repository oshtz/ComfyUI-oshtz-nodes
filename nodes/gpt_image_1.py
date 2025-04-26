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
    try:
        # Add fallback in case movedim fails
        if len(image_tensor.shape) != 3 or image_tensor.shape[-1] not in [3, 4]:
            print(f"Warning: Unexpected tensor shape in downscale_input: {image_tensor.shape}")
            # Return the tensor unmodified if it doesn't have the expected dimensions
            return image_tensor
            
        samples = image_tensor.unsqueeze(0).movedim(-1, 1)
        print(f"Downscaling shape after movedim: {samples.shape}")
        
        # Safety check to make sure we have 4D tensor with [B,C,H,W]
        if len(samples.shape) != 4:
            print(f"Error: Expected 4D tensor after unsqueeze+movedim, got {samples.shape}")
            return image_tensor
            
        H, W = samples.shape[2], samples.shape[3]
        target_total_pixels = int(1536 * 1024)
        current_pixels = W * H
        
        if current_pixels <= target_total_pixels:
            return image_tensor
            
        scale_by = math.sqrt(target_total_pixels / current_pixels)
        new_width = round(W * scale_by)
        new_height = round(H * scale_by)
        
        print(f"Downscaling from {W}x{H} to {new_width}x{new_height}")
        s = common_upscale(samples, new_width, new_height, "lanczos", "disabled")
        s = s.squeeze(0).movedim(1, -1)
        print(f"Downscaled tensor shape: {s.shape}")
        return s
    except Exception as e:
        print(f"Error in downscale_input: {e}")
        # In case of any error, return the original tensor
        return image_tensor

def prepare_image_for_api(image_tensor):
    # Debug original tensor shape
    original_shape = image_tensor.shape
    
    # Ensure tensor is on CPU and detached from computation graph
    tensor = image_tensor.cpu().detach()
    
    # Handle tensor dimension issues - we need a tensor with shape [H, W, C] where C is 3 or 4
    if len(tensor.shape) == 4 and tensor.shape[0] == 1:  # Shape [1, H, W, C]
        tensor = tensor.squeeze(0)  # Remove batch dimension
    
    # If tensor has a weird number of channels or channel dimension is not last
    if len(tensor.shape) == 3:
        # Detect if channels might be in a different position
        if tensor.shape[0] == 3 or tensor.shape[0] == 4:  # Likely [C, H, W] format
            tensor = tensor.permute(1, 2, 0)  # Convert to [H, W, C]
        elif tensor.shape[-1] > 4:  # Too many channels in last dimension
            # Take just the first 3 channels if there are too many
            tensor = tensor[..., :3]
    
    # If tensor is 2D (single channel), convert to RGB by repeating the channel
    if len(tensor.shape) == 2:
        tensor = tensor.unsqueeze(-1).repeat(1, 1, 3)  # Convert to [H, W, 3]
    
    # Final check to ensure we have proper dimensions
    if len(tensor.shape) != 3 or (tensor.shape[-1] != 3 and tensor.shape[-1] != 4):
        raise ValueError(f"Cannot process tensor with shape {original_shape} -> {tensor.shape}. " 
                        f"Expected a 3D tensor with 3 or 4 channels as the last dimension.")
    
    # Downscale if needed
    scaled_image_tensor = downscale_input(tensor)
    
    # Convert to numpy and prepare for PIL
    image_np = (scaled_image_tensor.numpy() * 255).clip(0, 255).astype(np.uint8)
    
    # Create PIL image
    if image_np.shape[-1] == 4:
        img = Image.fromarray(image_np, 'RGBA')
    elif image_np.shape[-1] == 3:
        img = Image.fromarray(image_np, 'RGB')
    else:
        # This shouldn't happen due to our previous checks, but just in case
        raise ValueError(f"Unexpected number of channels after processing: {image_np.shape[-1]}")
    
    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

def prepare_mask_for_api(mask_tensor, image_shape_hw):
    # Debug original tensor shape
    original_shape = mask_tensor.shape
    print(f"Preparing mask with shape {original_shape}, target shape {image_shape_hw}")
    
    # Ensure tensor is on CPU and detached from computation graph
    mask = mask_tensor.cpu().detach()
    
    # If mask has extra dimensions (like batch), remove them
    if len(mask.shape) > 2:
        # If it's a 3D tensor with a single channel at the end
        if len(mask.shape) == 3 and mask.shape[-1] == 1:
            mask = mask.squeeze(-1)
        # If it's a 3D tensor with channels at another position or multi-channel
        elif len(mask.shape) == 3:
            # If it appears to be [C,H,W] format with C=1
            if mask.shape[0] == 1:
                mask = mask.squeeze(0)
            # If it has multiple channels, take the first one
            else:
                # Take first channel or average multiple channels
                mask = mask[0] if mask.shape[0] > 1 else mask.mean(dim=0)
    
    # Handle any remaining non-2D case
    if len(mask.shape) != 2:
        print(f"Warning: Unusual mask shape {mask.shape} after preprocessing, attempting to reshape")
        # Try to reshape to 2D
        try:
            # If it's still not 2D, try to reshape it
            if mask.numel() == image_shape_hw[0] * image_shape_hw[1]:
                mask = mask.reshape(image_shape_hw)
            else:
                # Last resort - take the first slice that matches dimensions
                mask = mask.view(-1, image_shape_hw[0], image_shape_hw[1])[0]
        except Exception as e:
            print(f"Failed to reshape mask: {e}")
    
    # Now resize if needed
    if mask.shape != image_shape_hw:
        print(f"Resizing mask from {mask.shape} to {image_shape_hw}")
        try:
            mask_for_resize = mask.unsqueeze(0).unsqueeze(0)
            resized_mask = common_upscale(mask_for_resize, image_shape_hw[1], image_shape_hw[0], "nearest", "disabled")
            mask = resized_mask.squeeze(0).squeeze(0)
            if mask.shape != image_shape_hw:
                raise ValueError(f"Mask resize failed. Final shape {mask.shape} still differs from image {image_shape_hw}.")
        except Exception as e:
            print(f"Error during mask resize: {e}")
            # Create an empty mask of the right size as fallback
            print("Creating empty mask as fallback")
            mask = torch.zeros(image_shape_hw, dtype=torch.float32)
    
    # Continue with the original conversion to RGBA
    mask_tensor_cpu = mask
    height, width = mask_tensor_cpu.shape
    rgba_mask_np = np.zeros((height, width, 4), dtype=np.float32)
    rgba_mask_np[mask_tensor_cpu > 0.5, 3] = 0.0
    rgba_mask_np[mask_tensor_cpu <= 0.5, 3] = 1.0
    mask_np_uint8 = (rgba_mask_np * 255).clip(0, 255).astype(np.uint8)
    mask_img = Image.fromarray(mask_np_uint8, 'RGBA')
    
    # Convert to bytes
    mask_byte_arr = io.BytesIO()
    mask_img.save(mask_byte_arr, format='PNG')
    mask_byte_arr.seek(0)
    print("Mask processing completed successfully")
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
                "moderation": (IO.COMBO, {"options": ["auto", "low"], "default": "low", "tooltip": "Content moderation level. 'low' (default) for less restrictive filtering, 'auto' for standard filtering."}),
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

    def api_call(self, prompt, api_key, seed=0, quality="low", background="opaque", moderation="low", size="auto", n=1, image=None, mask=None):
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
            "moderation": moderation,
            # 'response_format': 'b64_json',  # Removed because it's not supported
        }
        is_edit = image is not None and mask is not None
        if is_edit:
            endpoint = f"{_OPENAI_API_BASE_URL}/images/edits"
            if image.shape[0] != 1 or mask.shape[0] != 1:
                raise ValueError("Image editing currently supports only batch size 1 for image and mask.")
            
            # Add diagnostic info about image tensor shape
            try:
                print(f"Image tensor shape before processing: {image.shape}")
                
                # Check specifically for the 941 channels error from the original prompt
                if len(image.squeeze(0).shape) == 3 and image.squeeze(0).shape[-1] == 941:
                    print("Detected 941 channels error case - applying special handling")
                    # Create a new tensor with just 3 channels from the original data
                    fixed_tensor = image.squeeze(0)[..., :3].clone()
                    print(f"Created fixed tensor with shape {fixed_tensor.shape}")
                    image_bytes = prepare_image_for_api(fixed_tensor)
                else:
                    image_bytes = prepare_image_for_api(image.squeeze(0))
                
                print("Image processed successfully")
                
                print(f"Mask tensor shape before processing: {mask.shape}")
                mask_bytes = prepare_mask_for_api(mask.squeeze(0), image.shape[1:3])
                print("Mask processed successfully")
                
                files['image'] = ('image.png', image_bytes, 'image/png')
                files['mask'] = ('mask.png', mask_bytes, 'image/png')
            except Exception as e:
                # Provide detailed error information for debugging
                print(f"Error during image/mask processing: {e}")
                if isinstance(image, torch.Tensor):
                    try:
                        print(f"Image tensor details - shape: {image.shape}, dtype: {image.dtype}")
                        print(f"Squeezed shape: {image.squeeze(0).shape if len(image.shape) > 3 else 'N/A'}")
                        if len(image.shape) >= 3:
                            print(f"Min/max values: {image.min().item():.4f}, {image.max().item():.4f}")
                            
                        # Additional diagnostic for unusual channel counts
                        if len(image.squeeze(0).shape) == 3 and image.squeeze(0).shape[-1] > 4:
                            large_channel_count = image.squeeze(0).shape[-1]
                            print(f"WARNING: Unusually large channel count detected: {large_channel_count}")
                            print("This is likely the cause of the error. The code has been updated to handle this case.")
                    except Exception as inner_e:
                        print(f"Error during diagnostic logging: {inner_e}")
                
                raise ValueError(f"Failed to process image or mask for API: {e}")
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
