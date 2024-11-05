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

### LoRA Switcher Node
- Easily switch between up to 10 different LoRA models in your workflow
- Adjust LoRA strength with fine-grained control (-10.0 to 10.0)
- Compatible with all standard LoRA models
- Seamless integration with existing ComfyUI workflows

## Installation

1. Navigate to your ComfyUI custom nodes directory:
```bash
cd ComfyUI/custom_nodes/
```

2. Clone this repository:
```bash
git clone https://github.com/oshtz/ComfyUI-oshtz-nodes.git
```

3. Install the required dependencies:
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
