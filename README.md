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

## Usage

### LoRA Switcher
1. Add the "LoRA Switcher" node to your workflow
2. Connect your base model and CLIP model
3. Select from up to 10 different LoRA models
4. Adjust the LoRA strength as needed
5. The node will output the modified model and CLIP

### LLM All-in-One
1. Add the "LLM All-in-One" node to your workflow
2. Choose your preferred API (OpenAI or Claude)
3. Select a model from the available options
4. Configure parameters:
   - Max tokens (1-8192)
   - Temperature (0-1.0)
   - Prompt text
   - Optional image input for vision models
5. Provide the necessary API keys in the node settings

## API Key Configuration
- For OpenAI models: Provide your OpenAI API key in the node settings
- For Claude models: Provide your Anthropic API key in the node settings
- For AWS Bedrock: Configure AWS credentials separately

## License
This project is open-source and available under the MIT License.
