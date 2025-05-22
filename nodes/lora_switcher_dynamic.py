import folder_paths
from nodes import LoraLoader
from ..utils import FlexibleOptionalInputType, any_type
import server # Import the server instance
from aiohttp import web # For JSON response
import json # Import json for parsing

class LoraSwitcherDynamic:
    """
    A node that dynamically loads LoRA configurations and applies only the one
    selected by the active_index.
    """
    CATEGORY = "oshtz Nodes"
    TITLE = "LoRA Switcher (Dynamic)"
    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("MODEL", "CLIP")
    FUNCTION = "apply_lora"

    @classmethod
    def INPUT_TYPES(cls):
        # Reverted: No longer fetching list here or passing hidden input
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "active_index": ("INT", {"default": 0, "min": 0, "step": 1}),
            },
            # This signals to the ComfyUI frontend that this node accepts
            # dynamically added inputs. The frontend script associated with
            # nodes like Power Lora Loader handles adding widgets for
            # lora_name, strength_model, strength_clip.
            # "optional": FlexibleOptionalInputType(any_type),
            # Optional is no longer needed as data comes via hidden input
            "hidden": {"lora_config": "STRING", "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}, # Add hidden input for config
        }

    def apply_lora(self, model, clip, active_index, lora_config=None, **kwargs):
        # --- Enhanced DEBUG logging --- 
        # print(f"\n{'='*80}")
        # print(f"{self.TITLE}: EXECUTION START")
        # print(f"Active Index: {active_index}")
        # print(f"LoRA Config Type: {type(lora_config)}")
        # print(f"LoRA Config Value: {lora_config}")
        
        # Debug all kwargs to see what's available
        # print(f"All kwargs keys: {list(kwargs.keys())}")
        # print(f"{'='*80}\n")
        # --- End enhanced DEBUG ---

        if active_index == 0:
            # print(f"{self.TITLE}: Active index is 0, bypassing LoRA loading.")
            return (model, clip)

        # Parse LoRA configurations from the hidden JSON input
        lora_configs = []
        if lora_config:
            try:
                # The config is expected to be a list of dicts like:
                # [{'lora': 'name1.safetensors', 'strength': 0.8}, ...]
                parsed_configs = json.loads(lora_config)
                # print(f"{self.TITLE}: Successfully parsed JSON. Type: {type(parsed_configs)}")
                
                if isinstance(parsed_configs, list):
                    # Basic validation: check if items are dicts with expected keys
                    for i, config in enumerate(parsed_configs):
                        if isinstance(config, dict) and 'lora' in config and 'strength' in config:
                            # print(f"{self.TITLE}: Valid config at index {i}: {config}")
                            lora_configs.append(config)
                        else:
                            print(f"{self.TITLE}: WARNING: Invalid config at index {i}: {config}")
                    
                    # print(f"{self.TITLE}: Found {len(lora_configs)} valid configs out of {len(parsed_configs)} total items")
                else:
                    print(f"{self.TITLE}: ERROR: Parsed lora_config is not a list: {type(parsed_configs)}")
            except json.JSONDecodeError as e:
                print(f"{self.TITLE}: ERROR: Failed to parse lora_config JSON: {e}")
                print(f"{self.TITLE}: Raw config: {repr(lora_config)[:100]}...")
            except Exception as e:
                print(f"{self.TITLE}: ERROR: Unexpected error processing lora_config: {e}")
        else:
             # print(f"{self.TITLE}: No lora_config received or it's empty/None.")
             pass

        if not lora_configs:
            # print(f"{self.TITLE}: No valid LoRA configurations found after parsing lora_config.")
            # print(f"{self.TITLE}: EXECUTION END - No valid configs\n")
            return (model, clip)

        # Adjust active_index to be 0-based for list access
        # Ensure active_index is treated as an integer
        try:
            active_index_int = int(active_index)
            # print(f"{self.TITLE}: Active index converted to int: {active_index_int}")
        except ValueError:
             print(f"{self.TITLE}: Invalid non-integer active_index received: {active_index}")
             # print(f"{self.TITLE}: EXECUTION END - Invalid active_index\n")
             return (model, clip)

        target_index = active_index_int - 1
        # print(f"{self.TITLE}: Target index (0-based) for list access: {target_index}")

        if target_index < 0:
            # print(f"{self.TITLE}: active_index {active_index} resolves to negative target index {target_index}")
            # print(f"{self.TITLE}: EXECUTION END - Negative target index\n")
            return (model, clip)
            
        if target_index >= len(lora_configs):
            # print(f"{self.TITLE}: active_index {active_index} (target: {target_index}) is out of range for the {len(lora_configs)} available LoRA(s).")
            # print(f"{self.TITLE}: EXECUTION END - Index out of range\n")
            return (model, clip)

        # Get the selected LoRA config
        selected_config = lora_configs[target_index]
        # print(f"{self.TITLE}: Selected config: {selected_config}")

        lora_name = selected_config.get('lora', 'None')
        strength_model = selected_config.get('strength', 0.0)
        # Use strength_model for both model and clip strength now
        strength_clip = strength_model
        
        # print(f"{self.TITLE}: Extracted values - LoRA: '{lora_name}', Strength: {strength_model}")

        if lora_name == "None" or lora_name is None:
            # print(f"{self.TITLE}: Selected LoRA at index {active_index} is 'None'.")
            # print(f"{self.TITLE}: EXECUTION END - 'None' LoRA selected\n")
            return (model, clip)

        if strength_model == 0 and strength_clip == 0:
            # print(f"{self.TITLE}: Selected LoRA '{lora_name}' at index {active_index} has zero strength.")
            # print(f"{self.TITLE}: EXECUTION END - Zero strength\n")
            return (model, clip)

        # Load the selected LoRA
        # print(f"{self.TITLE}: Attempting to apply LoRA '{lora_name}' (Index: {active_index}) with Model Strength: {strength_model}, Clip Strength: {strength_clip}")
        try:
            # Ensure lora_name is just the filename
            original_name = lora_name
            if '/' in lora_name or '\\' in lora_name:
                 lora_name = folder_paths.get_path_filename(lora_name)
                 # print(f"{self.TITLE}: Extracted filename from path: '{original_name}' -> '{lora_name}'")

            # Check if lora exists before loading
            lora_path = folder_paths.get_full_path("loras", lora_name)
            # print(f"{self.TITLE}: Looking for LoRA file: '{lora_name}'")
            
            if lora_path is None:
                 print(f"{self.TITLE}: ERROR: LoRA file not found: {lora_name}")
                 # print(f"{self.TITLE}: EXECUTION END - LoRA file not found\n")
                 # Optionally raise an error or just return original tensors
                 # Make sure to return original tensors
                 return (model, clip)
            else:
                 # print(f"{self.TITLE}: Found LoRA at path: {lora_path}")
                 pass

            # print(f"{self.TITLE}: Calling LoraLoader().load_lora...")
            model_lora, clip_lora = LoraLoader().load_lora(model, clip, lora_name, strength_model, strength_clip)
            # print(f"{self.TITLE}: LoRA application successful!")
            # print(f"{self.TITLE}: EXECUTION END - Success\n")
            return (model_lora, clip_lora)
        except Exception as e:
            print(f"{self.TITLE}: Failed to load LoRA '{lora_name}'. Error: {e}")
            import traceback
            print(f"{self.TITLE}: Traceback: {traceback.format_exc()}")
            # print(f"{self.TITLE}: EXECUTION END - Exception\n")
            # Fallback to returning original model/clip on error
            return (model, clip)


# --- Add Custom API Endpoint ---
@server.PromptServer.instance.routes.get("/oshtz-nodes/get-loras")
async def get_loras_endpoint(request):
    """Custom API endpoint to fetch the LoRA list."""
    try:
        lora_list = ["None"] + folder_paths.get_filename_list("loras")
        # print("[LoraSwitcherDynamic] Served LoRA list via custom endpoint.") # Add log
        return web.json_response(lora_list)
    except Exception as e:
        print(f"Error in /oshtz-nodes/get-loras endpoint: {e}")
        return web.json_response(["None", f"ERROR: {e}"], status=500)


# --- Serve static files for oshtz-nodes ---
import os as _os

try:
    static_dir_path = _os.path.join(_os.path.dirname(__file__), "..", "web")
    static_dir_path = _os.path.abspath(static_dir_path)
    # print(f"[oshtz-nodes] Serving static files from: {static_dir_path}")
    server.PromptServer.instance.app.router.add_static(
        "/extensions/ComfyUI-oshtz-nodes/", static_dir_path, show_index=True
    )
except Exception as e:
    print(f"[oshtz-nodes] Failed to add static file route: {e}")
