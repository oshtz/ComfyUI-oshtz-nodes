import folder_paths
from nodes import LoraLoader
from ..utils import FlexibleOptionalInputType, any_type
import server # Import the server instance
from aiohttp import web # For JSON response

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
            "optional": FlexibleOptionalInputType(any_type),
            "hidden": {}, # No hidden inputs needed now
        }

    def apply_lora(self, model, clip, active_index, **kwargs):
        # --- DEBUG: Print the received dynamic inputs ---
        print(f"DEBUG LoraSwitcherDynamic kwargs: {kwargs}")
        # --- End DEBUG ---

        if active_index == 0:
            print(f"{self.TITLE}: Active index is 0, bypassing LoRA loading.")
            return (model, clip)

        # Collect valid LoRA configurations from kwargs
        lora_configs = []

        # Define a helper function to extract the numerical index from keys like 'lora_1', 'lora_2'
        def get_lora_index(key):
            try:
                # Extract number after 'lora_'
                return int(key.split('_')[1])
            except (IndexError, ValueError):
                # Fallback for unexpected keys, place them last
                return float('inf')

        # Sort keys numerically based on the extracted index
        sorted_keys = sorted(kwargs.keys(), key=get_lora_index)

        for key in sorted_keys:
            # Use .get for safety in case a key is somehow missing after sorting (unlikely)
            value = kwargs.get(key)
            # Check if the value looks like a LoRA config added by a dynamic widget handler
            # (similar structure to rgthree's Power Lora Loader)
            # Simplified: Assume if the dict exists, it's 'on' because there's no toggle anymore
            # Also check if the key pattern matches, just in case other kwargs exist
            if key.startswith("lora_") and isinstance(value, dict) and 'lora' in value and 'strength' in value:
                lora_configs.append(value) # Directly add if structure matches

        if not lora_configs:
            print(f"{self.TITLE}: No LoRA configurations found in inputs.")
            return (model, clip)

        # Adjust active_index to be 0-based for list access
        # Ensure active_index is treated as an integer
        try:
            active_index_int = int(active_index)
        except ValueError:
             print(f"{self.TITLE}: Invalid non-integer active_index received: {active_index}")
             return (model, clip)

        target_index = active_index_int - 1

        if target_index < 0 or target_index >= len(lora_configs):
            print(f"{self.TITLE}: active_index {active_index} is out of range for the {len(lora_configs)} active LoRA(s).")
            return (model, clip)

        # Get the selected LoRA config
        selected_config = lora_configs[target_index]

        lora_name = selected_config.get('lora', 'None')
        strength_model = selected_config.get('strength', 0.0)
        # Use strength_model for both model and clip strength now
        strength_clip = strength_model

        if lora_name == "None" or lora_name is None:
            print(f"{self.TITLE}: Selected LoRA at index {active_index} is 'None'.")
            return (model, clip)

        if strength_model == 0 and strength_clip == 0:
            print(f"{self.TITLE}: Selected LoRA '{lora_name}' at index {active_index} has zero strength.")
            return (model, clip)

        # Load the selected LoRA
        print(f"{self.TITLE}: Applying LoRA '{lora_name}' (Index: {active_index}) with Model Strength: {strength_model}, Clip Strength: {strength_clip}")
        try:
            # Ensure lora_name is just the filename
            if '/' in lora_name or '\\' in lora_name:
                 lora_name = folder_paths.get_path_filename(lora_name)

            # Check if lora exists before loading
            lora_path = folder_paths.get_full_path("loras", lora_name)
            if lora_path is None:
                 print(f"{self.TITLE}: ERROR: LoRA file not found: {lora_name}")
                 # Optionally raise an error or just return model/clip
                 return (model, clip)

            model_lora, clip_lora = LoraLoader().load_lora(model, clip, lora_name, strength_model, strength_clip)
            return (model_lora, clip_lora)
        except Exception as e:
            print(f"{self.TITLE}: Failed to load LoRA '{lora_name}'. Error: {e}")
            # Fallback to returning original model/clip on error
            return (model, clip)


# --- Add Custom API Endpoint ---
@server.PromptServer.instance.routes.get("/oshtz-nodes/get-loras")
async def get_loras_endpoint(request):
    """Custom API endpoint to fetch the LoRA list."""
    try:
        lora_list = ["None"] + folder_paths.get_filename_list("loras")
        print("[LoraSwitcherDynamic] Served LoRA list via custom endpoint.") # Add log
        return web.json_response(lora_list)
    except Exception as e:
        print(f"Error in /oshtz-nodes/get-loras endpoint: {e}")
        return web.json_response(["None", f"ERROR: {e}"], status=500)


# --- Serve static files for oshtz-nodes ---
import os as _os

try:
    static_dir_path = _os.path.join(_os.path.dirname(__file__), "..", "web")
    static_dir_path = _os.path.abspath(static_dir_path)
    print(f"[oshtz-nodes] Serving static files from: {static_dir_path}")
    server.PromptServer.instance.app.router.add_static(
        "/extensions/ComfyUI-oshtz-nodes/", static_dir_path, show_index=True
    )
except Exception as e:
    print(f"[oshtz-nodes] Failed to add static file route: {e}")
