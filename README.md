# ComfyUI-oshtz-nodes

Custom nodes for ComfyUI created for practical prompt, LoRA, image API, and utility workflows.

## Nodes

### LLM All-in-One

Easy GPT, Claude, and OpenRouter integration in ComfyUI:

- OpenAI, Anthropic, and OpenRouter providers
- Live OpenRouter model list fetched through the node backend
- Image-to-text capabilities for vision-capable models
- API keys via widget inputs or environment variables:
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`

<div style="display: flex; align-items: center; justify-content: space-between;">
  <img src="https://github.com/oshtz/ComfyUI-oshtz-nodes/blob/main/examples/prompt_enhancer.jpg?raw=true" alt="Prompt enhancer example" height="250"/>
  <a href="https://youtu.be/0KZ7sMd4jUo">
    <img src="https://img.youtube.com/vi/0KZ7sMd4jUo/maxresdefault.jpg" alt="Watch the video" height="250"/>
  </a>
</div>

### LoRA Switcher (Dynamic)

Dynamic LoRA selection powered by a single configurable node:

- Drive LoRA choice via API-friendly widget data
- Unlimited rows with custom strengths managed from the UI
- Keeps workflows simpler than juggling fixed 10/20/40 variants

### GPT Image 1 (Direct API)

Generate or edit images through OpenAI's image API:

- Text-to-image generation
- Optional image and mask inputs for edits
- Environment variable fallback via `OPENAI_API_KEY`

### String Splitter

Split text into multiple outputs:

- Up to 10 separate outputs
- Customizable separator

### Easy Aspect Ratio

Select common image ratios and output ratio text, width, and height.

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
- pydantic
- Pillow
- numpy

ComfyUI provides the runtime tensor and image stack used by the nodes.

## License

This project is open-source and available under the MIT License.
