# ComfyUI-oshtz-nodes
Custom nodes for ComfyUI created for some of my workflows.

### LLM All-in-One Node
Connect your workflows to powerful language models:
- OpenAI GPT models
- Anthropic Claude models
- AWS Bedrock integration
- Image-to-text capabilities
- Adjustable temperature and token limits

### String Splitter Node
Split text into multiple outputs:
- Up to 10 separate outputs
- Customizable separator (default: comma)
- Handles empty values gracefully
- Ideal for:
  - CSV parsing
  - Prompt lists
  - Batch processing

### LoRA Switcher Node
Manage multiple LoRA models efficiently:
- Switch between up to 10 different LoRA models
- Fine-tune strength (-10.0 to 10.0)
- Compatible with standard LoRA models
- Seamless ComfyUI integration

### Image Overlay Node (Beta 🚧)
Combine images with precision:

**Current Features**
- Basic image compositing
- Position control (X/Y)
- Transparency adjustment
- Auto size matching
- Alpha channel support

**Coming Soon**
- Advanced positioning
- Transform controls
- Multiple blend modes
- Layer management
- Interactive preview

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