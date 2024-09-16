try:
    import comfy.utils
except ImportError:
    pass
else:
    from .nodes.lora_switcher import LoRASwitcherNode

    NODE_CLASS_MAPPINGS = {
        "LoRASwitcherNode": LoRASwitcherNode
    }

    NODE_DISPLAY_NAME_MAPPINGS = {
        "LoRASwitcherNode": LoRASwitcherNode.TITLE
    }

    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
