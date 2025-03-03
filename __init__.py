try:
    import comfy.utils
except ImportError:
    pass
else:
    from .nodes.lora_switcher import LoRASwitcherNode
    from .nodes.lora_switcher_20 import LoRASwitcherNode20 as LoRASwitcherNode20
    from .nodes.lora_switcher_40 import LoRASwitcherNode40
    from .nodes.llm_aio import LLMAIONode
    from .nodes.image_overlay import ImageOverlayNode
    from .nodes.string_splitter import StringSplitterNode
    from .nodes.aspect_ratio import EasyAspectRatioNode

    NODE_CLASS_MAPPINGS = {
        "LoRASwitcherNode": LoRASwitcherNode,
        "LoRASwitcherNode20": LoRASwitcherNode20,
        "LoRASwitcherNode40": LoRASwitcherNode40,
        "LLMAIONode": LLMAIONode,
        "ImageOverlayNode": ImageOverlayNode,
        "StringSplitterNode": StringSplitterNode,
        "EasyAspectRatioNode": EasyAspectRatioNode
    }

    NODE_DISPLAY_NAME_MAPPINGS = {
        "LoRASwitcherNode": LoRASwitcherNode.TITLE,
        "LoRASwitcherNode20": LoRASwitcherNode20.TITLE,
        "LoRASwitcherNode40": LoRASwitcherNode40.TITLE,
        "LLMAIONode": LLMAIONode.TITLE,
        "ImageOverlayNode": ImageOverlayNode.TITLE,
        "StringSplitterNode": StringSplitterNode.TITLE,
        "EasyAspectRatioNode": EasyAspectRatioNode.TITLE
    }

    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
