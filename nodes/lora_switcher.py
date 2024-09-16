from nodes import LoraLoader
from ..utils import update_dynamic_inputs, get_lora_list

class LoRASwitcherNode:
    TITLE = "LoRA Switcher"
    CATEGORY = "oshtz Nodes"
    RETURN_TYPES = ("MODEL", "CLIP")
    FUNCTION = "apply_lora"

    def __init__(self):
        self.num_loras = 4

    def INPUT_TYPES(self):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "num_loras": ("INT", {
                    "default": self.num_loras,
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
                "selected": (["None"] + [f"LoRA {i}" for i in range(1, self.num_loras + 1)],),
                **update_dynamic_inputs("LORA", self.num_loras, prefix="lora", options=get_lora_list())["required"]
            }
        }

    def apply_lora(self, model, clip, num_loras, lora_strength, selected, **kwargs):
        if num_loras != self.num_loras:
            self.num_loras = num_loras
            return {"ui": {"inputs": self.INPUT_TYPES()["required"]}}

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

    @classmethod
    def VALIDATE_INPUTS(cls, num_loras, **kwargs):
        return update_dynamic_inputs("LORA", num_loras, prefix="lora", options=get_lora_list())