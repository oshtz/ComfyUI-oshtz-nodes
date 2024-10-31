import torch

class StringSplitterNode:
    TITLE = "String Splitter"
    CATEGORY = "oshtz Nodes"
    RETURN_TYPES = ("STRING",) * 10
    RETURN_NAMES = tuple(f"output_{i+1}" for i in range(10))
    FUNCTION = "split_string"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_string": ("STRING", {"multiline": True}),
                "separator": ("STRING", {"default": ","}),
            }
        }

    def split_string(self, input_string, separator):
        parts = input_string.split(separator)
        outputs = parts[:10] + [''] * (10 - len(parts))
        return tuple(outputs)

NODE_CLASS_MAPPINGS = {
    "StringSplitterNode": StringSplitterNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StringSplitterNode": "String Splitter"
}