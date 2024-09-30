try:
    import comfy.utils
except ImportError:
    pass
else:
    from .nodes.lora_switcher import LoRASwitcherNode
    from .nodes.lora_switcher_20 import LoRASwitcherNode20 as LoRASwitcherNode20
    from .nodes.llm_aio import LLMAIONode

    NODE_CLASS_MAPPINGS = {
        "LoRASwitcherNode": LoRASwitcherNode,
        "LoRASwitcherNode20": LoRASwitcherNode20,
        "LLMAIONode": LLMAIONode
    }

    NODE_DISPLAY_NAME_MAPPINGS = {
        "LoRASwitcherNode": LoRASwitcherNode.TITLE,
        "LoRASwitcherNode20": LoRASwitcherNode20.TITLE,
        "LLMAIONode": LLMAIONode.TITLE
    }

    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
