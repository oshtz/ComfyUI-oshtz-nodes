try:
    import comfy.utils
except ImportError:
    pass
else:
    WEB_DIRECTORY = "web"
    from .nodes.lora_switcher_dynamic import LoraSwitcherDynamic
    from .nodes.llm_aio import LLMAIONode
    from .nodes.string_splitter import StringSplitterNode
    from .nodes.aspect_ratio import EasyAspectRatioNode
    from .nodes.gpt_image_1 import GPTImage1

    NODE_CLASS_MAPPINGS = {
        "LoraSwitcherDynamic": LoraSwitcherDynamic,
        "LLMAIONode": LLMAIONode,
        "StringSplitterNode": StringSplitterNode,
        "EasyAspectRatioNode": EasyAspectRatioNode,
        "GPTImage1": GPTImage1,
    }

    NODE_DISPLAY_NAME_MAPPINGS = {
        "LoraSwitcherDynamic": LoraSwitcherDynamic.TITLE,
        "LLMAIONode": LLMAIONode.TITLE,
        "StringSplitterNode": StringSplitterNode.TITLE,
        "EasyAspectRatioNode": EasyAspectRatioNode.TITLE,
        "GPTImage1": "GPT Image 1 (Direct API)",
    }

    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
