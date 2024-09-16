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
                "selected": (["None", "LoRA 1", "LoRA 2", "LoRA 3", "LoRA 4"],),
                "lora_1": (lora_list, ),
                "lora_2": (lora_list, ),
                "lora_3": (lora_list, ),
                "lora_4": (lora_list, ),
                "lora_strength": ("FLOAT", {
                    "default": 1.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.01
                }),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    FUNCTION = "apply_lora"

    def apply_lora(self, model, clip, selected, lora_1, lora_2, lora_3, lora_4, lora_strength):
        if selected == "None" or lora_strength == 0:
            return (model, clip)

        # Determine which LoRA to use based on the selection
        lora_name = None
        if selected == "LoRA 1":
            lora_name = lora_1
        elif selected == "LoRA 2":
            lora_name = lora_2
        elif selected == "LoRA 3":
            lora_name = lora_3
        elif selected == "LoRA 4":
            lora_name = lora_4

        # Check if the selected LoRA is valid
        if lora_name == "None" or not lora_name:
            return (model, clip)

        # Apply the selected LoRA
        model, clip = LoraLoader().load_lora(
            model, clip, lora_name, lora_strength, lora_strength
        )

        return (model, clip)