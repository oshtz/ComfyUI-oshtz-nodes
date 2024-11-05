# ComfyUI-oshtz-nodes
Custom nodes for ComfyUI created for some of my workflows.

### LLM All-in-One Node
- Support for multiple LLMs:
  - OpenAI GPT models
  - Anthropic Claude models
  - AWS Bedrock integration
- Image-to-text capabilities with compatible models
- Adjustable parameters for temperature and token limits
- Multi-line prompt support

### String Splitter Node
- Split a single input string into up to 10 separate outputs
- Configurable separator (default: comma)
- Perfect for:
  - Parsing comma-separated values
  - Breaking down prompt lists
  - Splitting text for batch processing
- Each output can be individually connected to other nodes
- Empty outputs are handled gracefully with blank strings
- Multiline text support

### LoRA Switcher Node
- Easily switch between up to 10 different LoRA models in your workflow
- Adjust LoRA strength with fine-grained control (-10.0 to 10.0)
- Compatible with all standard LoRA models
- Seamless integration with existing ComfyUI workflows

### Image Overlay Node (Work in Progress 🚧)
- Combine two images with overlay capabilities

#### Current Functionality
- Basic image compositing with:
  - Position control (X/Y coordinates)
  - Adjustable transparency (alpha: 0.0 - 1.0)
  - Automatic size matching of overlay to base image
  - Alpha channel support (RGBA conversion)
  - Transparent background handling

#### Planned Features
- Advanced positioning options:
  - Relative positioning (percentage-based)
  - Negative coordinates support
  - Anchor point selection (center, corners, etc.)
- Transform controls:
  - Scale/resize options
  - Rotation
  - Maintain aspect ratio option
- Advanced compositing:
  - Multiple blending modes (multiply, screen, overlay, etc.)
  - Multiple layer support
  - Masking capabilities
- Quality of life improvements:
  - Preview window
  - Interactive positioning
  - Preset positions (center, corners, etc.)

> ⚠️ Note: This node is in early development. Features and interface may change significantly in future updates.

## Installation

First navigate to your ComfyUI installation custom nodes directory.

1. Clone this repository:
```bash
git clone https://github.com/oshtz/ComfyUI-oshtz-nodes.git
```

2. Install the required dependencies:
```bash
cd ComfyUI-oshtz-nodes
pip install -r requirements.txt
```

## Requirements
- requests
- torch
- pydantic
- Pillow
- boto3 (>= 1.34.101)

## License
This project is open-source and available under the MIT License.
