import folder_paths
from nodes import LoraLoader

# Original LoRA Switcher Node
class LoRASwitcherNode:
    TITLE = "LoRA Switcher"
    CATEGORY = "oshtz Nodes"
    RETURN_TYPES = ("MODEL", "CLIP")
    FUNCTION = "apply_lora"

    @classmethod
    def INPUT_TYPES(cls):
        lora_list = ["None"] + folder_paths.get_filename_list("loras")
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "lora_strength": ("FLOAT", {
                    "default": 1.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.01
                }),
                "selected": (["None"] + [f"LoRA {i}" for i in range(1, 11)],),
                "lora_1": (lora_list,),
                "lora_2": (lora_list,),
                "lora_3": (lora_list,),
                "lora_4": (lora_list,),
                "lora_5": (lora_list,),
                "lora_6": (lora_list,),
                "lora_7": (lora_list,),
                "lora_8": (lora_list,),
                "lora_9": (lora_list,),
                "lora_10": (lora_list,),
            }
        }

    def apply_lora(self, model, clip, lora_strength, selected, lora_1, lora_2, lora_3, lora_4, lora_5, lora_6, lora_7, lora_8, lora_9, lora_10):
        if selected == "None" or lora_strength == 0:
            return (model, clip)

        # Determine which LoRA to use based on the selection
        lora_name = None
        for i in range(1, 11):
            if selected == f"LoRA {i}":
                lora_name = locals()[f"lora_{i}"]
                break

        # Check if the selected LoRA is valid
        if lora_name == "None" or not lora_name:
            return (model, clip)

        # Apply the selected LoRA
        model, clip = LoraLoader().load_lora(
            model, clip, lora_name, lora_strength, lora_strength
        )

        return (model, clip)
