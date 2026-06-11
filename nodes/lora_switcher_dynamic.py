import json
import traceback
from typing import Any, Dict, List, Optional

try:
    import folder_paths
    from nodes import LoraLoader
except ImportError:
    folder_paths = None
    LoraLoader = None

try:
    import server
    from aiohttp import web
except ImportError:
    server = None
    web = None


LORA_NONE = "None"


def parse_lora_config(lora_config: Any) -> List[Dict[str, Any]]:
    if not lora_config:
        return []

    try:
        parsed_configs = json.loads(lora_config) if isinstance(lora_config, str) else lora_config
    except json.JSONDecodeError as err:
        print(f"[LoraSwitcherDynamic] Failed to parse lora_config JSON: {err}")
        return []

    if not isinstance(parsed_configs, list):
        print(f"[LoraSwitcherDynamic] Expected lora_config list, got {type(parsed_configs).__name__}")
        return []

    configs = []
    for index, config in enumerate(parsed_configs):
        if not isinstance(config, dict):
            print(f"[LoraSwitcherDynamic] Ignoring invalid config at index {index}: {config}")
            continue

        lora_name = config.get("lora", LORA_NONE)
        if lora_name is None:
            lora_name = LORA_NONE
        if not isinstance(lora_name, str):
            print(f"[LoraSwitcherDynamic] Ignoring config with non-string lora at index {index}: {config}")
            continue

        try:
            strength_model = float(config.get("strength_model", config.get("strength", 0.0)))
            strength_clip = float(config.get("strength_clip", config.get("strength", strength_model)))
        except (TypeError, ValueError):
            print(f"[LoraSwitcherDynamic] Ignoring config with invalid strength at index {index}: {config}")
            continue

        configs.append(
            {
                "lora": lora_name,
                "strength_model": strength_model,
                "strength_clip": strength_clip,
            }
        )
    return configs


def select_lora_config(lora_configs: List[Dict[str, Any]], active_index: Any) -> Optional[Dict[str, Any]]:
    try:
        active_index_int = int(active_index)
    except (TypeError, ValueError):
        print(f"[LoraSwitcherDynamic] Invalid active_index received: {active_index}")
        return None

    if active_index_int <= 0:
        return None

    target_index = active_index_int - 1
    if target_index >= len(lora_configs):
        return None
    return lora_configs[target_index]


def normalize_lora_name(lora_name: str) -> str:
    if folder_paths is not None and ("/" in lora_name or "\\" in lora_name):
        return folder_paths.get_path_filename(lora_name)
    return lora_name


class LoraSwitcherDynamic:
    """
    Applies one selected LoRA from a frontend-managed JSON row config.
    """

    CATEGORY = "oshtz Nodes"
    TITLE = "LoRA Switcher (Dynamic)"
    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("MODEL", "CLIP")
    FUNCTION = "apply_lora"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "active_index": ("INT", {"default": 0, "min": 0, "step": 1}),
            },
            "hidden": {"lora_config": "STRING", "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    def apply_lora(self, model, clip, active_index, lora_config=None, **kwargs):
        selected_config = select_lora_config(parse_lora_config(lora_config), active_index)
        if not selected_config:
            return (model, clip)

        lora_name = selected_config["lora"]
        strength_model = selected_config["strength_model"]
        strength_clip = selected_config["strength_clip"]

        if lora_name == LORA_NONE or strength_model == 0 and strength_clip == 0:
            return (model, clip)

        if folder_paths is None or LoraLoader is None:
            print(f"{self.TITLE}: ComfyUI LoRA APIs are unavailable.")
            return (model, clip)

        lora_name = normalize_lora_name(lora_name)
        lora_path = folder_paths.get_full_path("loras", lora_name)
        if lora_path is None:
            print(f"{self.TITLE}: LoRA file not found: {lora_name}")
            return (model, clip)

        try:
            model_lora, clip_lora = LoraLoader().load_lora(model, clip, lora_name, strength_model, strength_clip)
            return (model_lora, clip_lora)
        except Exception as err:
            print(f"{self.TITLE}: Failed to load LoRA '{lora_name}'. Error: {err}")
            print(f"{self.TITLE}: Traceback: {traceback.format_exc()}")
            return (model, clip)


async def get_loras_endpoint(request):
    try:
        lora_list = [LORA_NONE] + folder_paths.get_filename_list("loras")
        return web.json_response(lora_list)
    except Exception as err:
        print(f"Error in /oshtz-nodes/get-loras endpoint: {err}")
        return web.json_response([LORA_NONE, f"ERROR: {err}"], status=500)


def register_routes():
    if server is None or web is None or folder_paths is None:
        return
    server.PromptServer.instance.routes.get("/oshtz-nodes/get-loras")(get_loras_endpoint)


register_routes()
