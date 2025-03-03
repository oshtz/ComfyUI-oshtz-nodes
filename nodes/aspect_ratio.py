class EasyAspectRatioNode:
    TITLE = "Easy Aspect Ratio"
    CATEGORY = "oshtz Nodes"
    RETURN_TYPES = ("STRING", "INT", "INT")
    RETURN_NAMES = ("ratio", "width", "height")
    FUNCTION = "get_aspect_ratio"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (
                    [
                        # Original ratios
                        "1:1",
                        "2:3", "3:4", "5:8", "9:16", "9:19", "9:21",
                        "3:2", "4:3", "8:5", "16:9", "19:9", "21:9",
                        # New additional ratios
                        "1:2", "2:1", "4:5", "5:4", "3:1", "1:3", "4:1", 
                        "1:4", "7:4", "4:7", "16:10", "10:16"
                    ],
                ),
            }
        }

    def get_aspect_ratio(self, aspect_ratio):
        width, height = 1024, 1024  # Default square

        # Original aspect ratios from the provided code
        if aspect_ratio == "1:1":
            width, height = 1024, 1024
        elif aspect_ratio == "2:3":
            width, height = 832, 1216
        elif aspect_ratio == "3:4":
            width, height = 896, 1152
        elif aspect_ratio == "5:8":
            width, height = 768, 1216
        elif aspect_ratio == "9:16":
            width, height = 768, 1344
        elif aspect_ratio == "9:19":
            width, height = 704, 1472
        elif aspect_ratio == "9:21":
            width, height = 640, 1536
        elif aspect_ratio == "3:2":
            width, height = 1216, 832
        elif aspect_ratio == "4:3":
            width, height = 1152, 896
        elif aspect_ratio == "8:5":
            width, height = 1216, 768
        elif aspect_ratio == "16:9":
            width, height = 1344, 768
        elif aspect_ratio == "19:9":
            width, height = 1472, 704
        elif aspect_ratio == "21:9":
            width, height = 1536, 640
        
        # New additional aspect ratios
        elif aspect_ratio == "1:2":
            width, height = 768, 1536
        elif aspect_ratio == "2:1":
            width, height = 1536, 768
        elif aspect_ratio == "4:5":
            width, height = 896, 1120
        elif aspect_ratio == "5:4":
            width, height = 1120, 896
        elif aspect_ratio == "3:1":
            width, height = 1536, 512
        elif aspect_ratio == "1:3":
            width, height = 512, 1536
        elif aspect_ratio == "4:1":
            width, height = 1536, 384
        elif aspect_ratio == "1:4":
            width, height = 384, 1536
        elif aspect_ratio == "7:4":
            width, height = 1344, 768
        elif aspect_ratio == "4:7":
            width, height = 768, 1344
        elif aspect_ratio == "16:10":
            width, height = 1280, 800
        elif aspect_ratio == "10:16":
            width, height = 800, 1280

        # Ensure dimensions are multiples of 8 (common requirement for AI image generation)
        width = (width // 8) * 8
        height = (height // 8) * 8

        return (aspect_ratio, width, height)


# Register the node
NODE_CLASS_MAPPINGS = {
    "EasyAspectRatioNode": EasyAspectRatioNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EasyAspectRatioNode": "Easy Aspect Ratio"
}
