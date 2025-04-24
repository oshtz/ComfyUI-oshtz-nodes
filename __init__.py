try:
    import comfy.utils
except ImportError:
    pass
else:
    WEB_DIRECTORY = "web"
    # Import all LoRA switchers
    from .nodes.lora_switcher import LoRASwitcherNode
    from .nodes.lora_switcher_20 import LoRASwitcherNode20
    from .nodes.lora_switcher_40 import LoRASwitcherNode40
    from .nodes.lora_switcher_dynamic import LoraSwitcherDynamic
    # Other node imports
    from .nodes.llm_aio import LLMAIONode
    from .nodes.string_splitter import StringSplitterNode
    from .nodes.aspect_ratio import EasyAspectRatioNode
    from .nodes.gpt_image_1 import GPTImage1

    # Define node mappings with all LoRA switchers
    NODE_CLASS_MAPPINGS = {
        # Old LoRA switchers
        "LoRASwitcherNode": LoRASwitcherNode,
        "LoRASwitcherNode20": LoRASwitcherNode20,
        "LoRASwitcherNode40": LoRASwitcherNode40,
        # New LoRA switcher
        "LoraSwitcherDynamic": LoraSwitcherDynamic,
        # Other nodes
        "LLMAIONode": LLMAIONode,
        "StringSplitterNode": StringSplitterNode,
        "EasyAspectRatioNode": EasyAspectRatioNode,
        "GPTImage1": GPTImage1,
    }

    # Define display name mappings
    NODE_DISPLAY_NAME_MAPPINGS = {
        # Old LoRA switchers
        "LoRASwitcherNode": LoRASwitcherNode.TITLE,
        "LoRASwitcherNode20": LoRASwitcherNode20.TITLE,
        "LoRASwitcherNode40": LoRASwitcherNode40.TITLE,
        # New LoRA switcher
        "LoraSwitcherDynamic": LoraSwitcherDynamic.TITLE,
        # Other nodes
        "LLMAIONode": LLMAIONode.TITLE,
        "StringSplitterNode": StringSplitterNode.TITLE,
        "EasyAspectRatioNode": EasyAspectRatioNode.TITLE,
        "GPTImage1": "GPT Image 1 (Direct API)",
    }

    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
