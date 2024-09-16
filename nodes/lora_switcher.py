from nodes import LoraLoader
import folder_paths

class LoRASwitcherNode:

    def __init__(self):
        pass

    NAME = "LoRA Switcher"
    TITLE = NAME
    CATEGORY = "Custom Nodes"

    @classmethod
    def INPUT_TYPES(cls):
        lora_list = ['None'] + folder_paths.get_filename_list("loras")
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "num_loras": ("INT", {
                    "default": 4,
                    "min": 1,
                    "max": 10,
                    "step": 1
                }),
                "lora_strength": ("FLOAT", {
                    "default": 1.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.01
                }),
                "selected": (["None"] + [f"LoRA {i+1}" for i in range(10)],),
            },
            "optional": {
                **{f"lora_{i+1}": (lora_list,) for i in range(10)}
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    FUNCTION = "apply_lora"

    def apply_lora(self, model, clip, num_loras, lora_strength, selected, **kwargs):
        if selected == "None" or lora_strength == 0:
            return (model, clip)

        # Determine which LoRA to use based on the selection
        lora_name = None
        for i in range(1, num_loras + 1):
            if selected == f"LoRA {i}":
                lora_name = kwargs.get(f"lora_{i}")
                break

        # Check if the selected LoRA is valid
        if lora_name == "None" or not lora_name:
            return (model, clip)

        # Apply the selected LoRA
        model, clip = LoraLoader().load_lora(
            model, clip, lora_name, lora_strength, lora_strength
        )

        return (model, clip)