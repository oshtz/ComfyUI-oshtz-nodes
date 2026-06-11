import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import requests
from pydantic import BaseModel
from torch import Tensor

from ..utils import pil2base64, tensor2pil

try:
    import server
    from aiohttp import web
except ImportError:
    server = None
    web = None


OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
    "o1-preview",
    "o1-mini",
]
OPENAI_VISION_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
]
CLAUDE_MODELS = [
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-2.1",
]
OPENROUTER_FALLBACK_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-haiku",
    "google/gemini-pro-1.5",
]
OPENROUTER_MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"
OPENROUTER_CACHE_TTL = 3600
OPENROUTER_MODELS_CACHE = {
    "timestamp": 0.0,
    "models": [],
}


def _dedupe_ordered(values: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _resolve_secret(widget_value: Optional[str], *env_names: str) -> str:
    if widget_value and widget_value.strip():
        return widget_value.strip()
    for env_name in env_names:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return ""


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int) -> Dict[str, Any]:
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    try:
        data = response.json()
    except ValueError as err:
        response.raise_for_status()
        raise RuntimeError(f"Provider returned a non-JSON response from {url}") from err

    if response.status_code >= 400:
        message = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else None
        raise RuntimeError(message or response.text)

    error = data.get("error")
    if error:
        raise RuntimeError(error.get("message", str(error)) if isinstance(error, dict) else str(error))
    return data


def get_openrouter_models(force_refresh: bool = False) -> List[str]:
    now = time.time()
    cached_models = OPENROUTER_MODELS_CACHE.get("models") or []
    cache_age = now - float(OPENROUTER_MODELS_CACHE.get("timestamp") or 0)
    if cached_models and not force_refresh and cache_age < OPENROUTER_CACHE_TTL:
        return cached_models

    try:
        response = requests.get(OPENROUTER_MODELS_ENDPOINT, timeout=15)
        response.raise_for_status()
        data = response.json()
        models = [
            model["id"]
            for model in data.get("data", [])
            if isinstance(model, dict) and isinstance(model.get("id"), str)
        ]
        models = _dedupe_ordered(models)
        if models:
            OPENROUTER_MODELS_CACHE["models"] = models
            OPENROUTER_MODELS_CACHE["timestamp"] = now
            return models
    except Exception as err:
        print(f"[LLM AIO] Failed to refresh OpenRouter models: {err}")

    return cached_models or OPENROUTER_FALLBACK_MODELS


def get_models_by_provider(force_refresh_openrouter: bool = False) -> Dict[str, List[str]]:
    return {
        "openai": OPENAI_MODELS,
        "claude": CLAUDE_MODELS,
        "openrouter": get_openrouter_models(force_refresh=force_refresh_openrouter),
    }


def get_static_model_options() -> List[str]:
    return _dedupe_ordered(OPENAI_MODELS + CLAUDE_MODELS + OPENROUTER_FALLBACK_MODELS)


class LLMConfig(BaseModel):
    model: str
    max_token: int
    temperature: float


class LLMMessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class LLMMessage(BaseModel):
    role: LLMMessageRole = LLMMessageRole.user
    content: List[Dict[str, Any]]

    @classmethod
    def create(cls, role: LLMMessageRole, text: str, image: Optional[str] = None):
        content = [{"type": "text", "text": text}]
        if image:
            content.insert(
                0,
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image,
                    },
                },
            )
        return cls(role=role, content=content)

    def to_openai_message(self):
        if len(self.content) == 1 and self.content[0]["type"] == "text":
            return {
                "role": self.role,
                "content": self.content[0]["text"],
            }

        openai_content = []
        for item in self.content:
            if item.get("type") == "image" and "source" in item:
                source = item["source"]
                if source.get("type") == "base64":
                    openai_content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{source.get('media_type', 'image/png')};base64,{source.get('data', '')}",
                                "detail": "auto",
                            },
                        }
                    )
            elif item.get("type") == "text":
                openai_content.append(item)

        return {
            "role": self.role,
            "content": openai_content,
        }

    def to_claude_message(self):
        return {
            "role": self.role,
            "content": self.content,
        }


class OpenAIApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://api.openai.com/v1"
    timeout: Optional[int] = 60

    def chat(self, messages: List[LLMMessage], config: LLMConfig, seed=None):
        payload = {
            "messages": [m.to_openai_message() for m in messages],
            "model": config.model,
            "max_tokens": config.max_token,
            "temperature": config.temperature,
        }
        if seed:
            payload["seed"] = seed
        data = _post_json(
            f"{self.endpoint}/chat/completions",
            payload,
            {"Authorization": f"Bearer {self.api_key}"},
            self.timeout,
        )
        return data["choices"][0]["message"]["content"]

    def complete(self, prompt: str, config: LLMConfig, seed=None):
        messages = [LLMMessage.create(role=LLMMessageRole.user, text=prompt)]
        return self.chat(messages, config, seed)


class OpenRouterApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://openrouter.ai/api/v1"
    timeout: Optional[int] = 60
    referer: Optional[str] = None
    title: Optional[str] = None

    def chat(self, messages: List[LLMMessage], config: LLMConfig, seed=None):
        payload = {
            "messages": [m.to_openai_message() for m in messages],
            "model": config.model,
            "max_tokens": config.max_token,
            "temperature": config.temperature,
        }
        if seed:
            payload["seed"] = seed
        data = _post_json(
            f"{self.endpoint}/chat/completions",
            payload,
            {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": self.referer or "https://comfyui",
                "X-Title": self.title or "ComfyUI oshtz nodes",
            },
            self.timeout,
        )
        return data["choices"][0]["message"]["content"]

    def complete(self, prompt: str, config: LLMConfig, seed=None):
        messages = [LLMMessage.create(role=LLMMessageRole.user, text=prompt)]
        return self.chat(messages, config, seed)


class ClaudeApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://api.anthropic.com/v1"
    version: Optional[str] = "2023-06-01"
    timeout: Optional[int] = 60

    def chat(self, messages: List[LLMMessage], config: LLMConfig):
        system_message = next((m for m in messages if m.role == LLMMessageRole.system), None)
        user_messages = [m for m in messages if m.role != LLMMessageRole.system]
        payload = {
            "messages": [m.to_claude_message() for m in user_messages],
            "model": config.model,
            "max_tokens": config.max_token,
            "temperature": config.temperature,
        }
        if system_message:
            payload["system"] = system_message.content[0]["text"]
        data = _post_json(
            f"{self.endpoint}/messages",
            payload,
            {
                "x-api-key": self.api_key,
                "anthropic-version": self.version,
                "Content-Type": "application/json",
            },
            self.timeout,
        )
        return data["content"][0]["text"]

    def complete(self, prompt: str, config: LLMConfig):
        messages = [LLMMessage.create(role=LLMMessageRole.user, text=prompt)]
        return self.chat(messages, config)


LLMApi = Union[OpenAIApi, ClaudeApi, OpenRouterApi]


class LLMAIONode:
    TITLE = "LLM All-In-One"
    CATEGORY = "oshtz Nodes"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)
    FUNCTION = "process"

    @classmethod
    def INPUT_TYPES(cls):
        key_help = "Optional. Leave blank to use the matching environment variable."
        return {
            "required": {
                "api_type": (["openai", "claude", "openrouter"],),
                "model": (
                    get_static_model_options(),
                    {"default": OPENAI_VISION_MODELS[0]},
                ),
                "max_token": ("INT", {"default": 1024, "min": 1, "max": 32768}),
                "temperature": ("FLOAT", {"default": 0, "min": 0, "max": 2.0, "step": 0.01}),
                "prompt": ("STRING", {"multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0x1FFFFFFFFFFFFF}),
            },
            "optional": {
                "openai_api_key": ("STRING", {"multiline": False, "default": "", "tooltip": key_help, "password": True}),
                "anthropic_api_key": ("STRING", {"multiline": False, "default": "", "tooltip": key_help, "password": True}),
                "openrouter_api_key": ("STRING", {"multiline": False, "default": "", "tooltip": key_help, "password": True}),
                "openrouter_referer": ("STRING", {"multiline": False, "default": ""}),
                "openrouter_app_title": ("STRING", {"multiline": False, "default": ""}),
                "model_override": ("STRING", {"multiline": False, "default": "", "tooltip": "Optional typed model id. Overrides the dropdown."}),
                "image": ("IMAGE",),
            },
        }

    def process(
        self,
        api_type,
        model,
        max_token,
        temperature,
        prompt,
        seed,
        model_override="",
        openai_api_key=None,
        anthropic_api_key=None,
        openrouter_api_key=None,
        openrouter_referer=None,
        openrouter_app_title=None,
        image: Optional[Tensor] = None,
    ):
        selected_model = model_override.strip() if model_override and model_override.strip() else model
        config = LLMConfig(
            model=selected_model,
            max_token=max_token,
            temperature=temperature,
        )

        if api_type == "openai":
            api_key = _resolve_secret(openai_api_key, "OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key is required. Provide it in the node or set OPENAI_API_KEY.")
            api = OpenAIApi(api_key=api_key)
        elif api_type == "claude":
            api_key = _resolve_secret(anthropic_api_key, "ANTHROPIC_API_KEY", "CLAUDE_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key is required. Provide it in the node or set ANTHROPIC_API_KEY.")
            api = ClaudeApi(api_key=api_key)
        elif api_type == "openrouter":
            api_key = _resolve_secret(openrouter_api_key, "OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OpenRouter API key is required. Provide it in the node or set OPENROUTER_API_KEY.")
            api = OpenRouterApi(
                api_key=api_key,
                referer=openrouter_referer,
                title=openrouter_app_title,
            )
        else:
            raise ValueError(f"Unsupported API type: {api_type}")

        if image is not None:
            image_content = pil2base64(tensor2pil(image))
            message = LLMMessage.create(role=LLMMessageRole.user, text=prompt, image=image_content)
        else:
            message = LLMMessage.create(role=LLMMessageRole.user, text=prompt)

        if api_type in {"openai", "openrouter"}:
            response = api.chat([message], config, seed=seed or None)
        else:
            response = api.chat([message], config)
        return (response,)


NODE_CLASS_MAPPINGS = {
    "LLMAIONode": LLMAIONode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLMAIONode": "LLM All-In-One",
}


if server and web:
    @server.PromptServer.instance.routes.get("/oshtz-nodes/llm-models")
    async def get_llm_models(request):
        provider = request.rel_url.query.get("provider")
        force_refresh = request.rel_url.query.get("force", "0") == "1"
        if provider:
            provider = provider.lower()
            if provider == "openrouter":
                models = get_openrouter_models(force_refresh=force_refresh)
            else:
                models = get_models_by_provider(force_refresh_openrouter=force_refresh).get(provider, [])
            return web.json_response({"provider": provider, "models": models})
        data = get_models_by_provider(force_refresh_openrouter=force_refresh)
        return web.json_response(data)
