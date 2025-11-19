import os
import json
import requests
import random
import time
import hashlib
from enum import Enum
from typing import List, Dict, Union, Optional, Any
import torch
from torch import Tensor
from pydantic import BaseModel
import base64
import io
from ..utils import ensure_package, tensor2pil, pil2base64

try:
    import server
    from aiohttp import web
except ImportError:
    server = None
    web = None

# Constants and model lists
aws_regions = [
    "us-east-1", "us-west-2", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
    "eu-central-1", "eu-west-3", "eu-west-1", "ap-south-3",
]
bedrock_anthropic_versions = ["bedrock-2023-05-31"]
bedrock_claude3_models = [
    "anthropic.claude-3-haiku-20240307", "anthropic.claude-3-sonnet-20240229",
    "anthropic.claude-3-opus-20240229", "anthropic.claude-3-5-sonnet-20240620",
]
bedrock_claude2_models = ["anthropic.claude-v2", "anthropic.claude-v2.1"]
bedrock_mistral_models = [
    "mistral.mistral-7b-instruct-v0:2", "mistral.mixtral-8x7b-instruct-v0:1",
    "mistral.mistral-large-2402-v1:0",
]
OPENROUTER_MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"
OPENROUTER_CACHE_TTL = 3600  # seconds
OPENROUTER_MODELS_CACHE = {"timestamp": 0, "models": []}
OPENROUTER_DEFAULT_REFERER = "https://comfyui"
OPENROUTER_DEFAULT_APP_TITLE = "ComfyUI oshtz Nodes"
OPENAI_MODELS_ENDPOINT = "https://api.openai.com/v1/models"
OPENAI_CACHE_TTL = 3600  # seconds
OPENAI_MODELS_CACHE: Dict[str, Dict[str, Any]] = {}
ANTHROPIC_MODELS_ENDPOINT = "https://api.anthropic.com/v1/models"
ANTHROPIC_CACHE_TTL = 3600  # seconds
ANTHROPIC_MODELS_CACHE: Dict[str, Dict[str, Any]] = {}
ANTHROPIC_DEFAULT_VERSION = "2023-06-01"
GEMINI_MODELS_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_CACHE_TTL = 3600  # seconds
GEMINI_MODELS_CACHE: Dict[str, Dict[str, Any]] = {}


def get_openrouter_models(force_refresh: bool = False) -> List[str]:
    """Fetch the latest OpenRouter models with caching and fallbacks."""
    now = time.time()
    cached_models = OPENROUTER_MODELS_CACHE.get("models") or []
    if (
        not force_refresh
        and cached_models
        and now - OPENROUTER_MODELS_CACHE.get("timestamp", 0) < OPENROUTER_CACHE_TTL
    ):
        return cached_models

    try:
        response = requests.get(OPENROUTER_MODELS_ENDPOINT, timeout=15)
        response.raise_for_status()
        data = response.json()
        models = [
            model["id"]
            for model in data.get("data", [])
            if isinstance(model, dict) and "id" in model
        ]
        if models:
            OPENROUTER_MODELS_CACHE["models"] = models
            OPENROUTER_MODELS_CACHE["timestamp"] = now
            return models
    except Exception as err:
        print(f"[LLM AIO] Failed to refresh OpenRouter models: {err}")

    return cached_models


def _hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def get_openai_models(api_key: Optional[str] = None, force_refresh: bool = False) -> List[str]:
    """Fetch OpenAI models when an API key is provided. Returns an empty list without a key."""
    if not api_key:
        return []
    cache_key = _hash_api_key(api_key)
    cache_entry = OPENAI_MODELS_CACHE.setdefault(cache_key, {"models": [], "timestamp": 0.0, "error": None})
    cached_models = cache_entry.get("models") or []
    last_refresh = cache_entry.get("timestamp", 0)
    now = time.time()
    if (
        cached_models
        and not force_refresh
        and now - last_refresh < OPENAI_CACHE_TTL
    ):
        return cached_models
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(OPENAI_MODELS_ENDPOINT, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        models = [
            model["id"]
            for model in data.get("data", [])
            if isinstance(model, dict) and "id" in model
        ]
        if models:
            cache_entry["models"] = models
            cache_entry["timestamp"] = now
            cache_entry["error"] = None
            return models
    except Exception as err:
        message = f"[LLM AIO] Failed to refresh OpenAI models: {err}"
        print(message)
        cache_entry["error"] = message
    return cached_models


def get_openai_models_error(api_key: Optional[str] = None) -> Optional[str]:
    if not api_key:
        return None
    cache_key = _hash_api_key(api_key)
    cache_entry = OPENAI_MODELS_CACHE.get(cache_key)
    if not cache_entry:
        return None
    return cache_entry.get("error")


def get_anthropic_models(
    api_key: Optional[str] = None,
    version: Optional[str] = None,
    force_refresh: bool = False,
) -> List[str]:
    """Fetch Anthropic models when an API key is provided. Returns an empty list without a key."""
    if not api_key:
        return []
    resolved_version = version or ANTHROPIC_DEFAULT_VERSION
    cache_key = f"{_hash_api_key(api_key)}::{resolved_version}"
    cache_entry = ANTHROPIC_MODELS_CACHE.setdefault(cache_key, {"models": [], "timestamp": 0.0, "error": None})
    cached_models = cache_entry.get("models") or []
    last_refresh = cache_entry.get("timestamp", 0)
    now = time.time()
    if (
        cached_models
        and not force_refresh
        and now - last_refresh < ANTHROPIC_CACHE_TTL
    ):
        return cached_models
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": resolved_version,
        }
        response = requests.get(ANTHROPIC_MODELS_ENDPOINT, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        models = [
            model["id"]
            for model in data.get("data", [])
            if isinstance(model, dict) and "id" in model
        ]
        if models:
            cache_entry["models"] = models
            cache_entry["timestamp"] = now
            cache_entry["error"] = None
            return models
    except Exception as err:
        message = f"[LLM AIO] Failed to refresh Anthropic models: {err}"
        print(message)
        cache_entry["error"] = message
    return cached_models


def get_anthropic_models_error(api_key: Optional[str] = None, version: Optional[str] = None) -> Optional[str]:
    if not api_key:
        return None
    resolved_version = version or ANTHROPIC_DEFAULT_VERSION
    cache_key = f"{_hash_api_key(api_key)}::{resolved_version}"
    cache_entry = ANTHROPIC_MODELS_CACHE.get(cache_key)
    if not cache_entry:
        return None
    return cache_entry.get("error")


def get_gemini_models(api_key: Optional[str] = None, force_refresh: bool = False) -> List[str]:
    """Fetch Gemini models when an API key is provided. Returns an empty list without a key."""
    if not api_key:
        return []
    cache_key = _hash_api_key(api_key)
    cache_entry = GEMINI_MODELS_CACHE.setdefault(cache_key, {"models": [], "timestamp": 0.0, "error": None})
    cached_models = cache_entry.get("models") or []
    last_refresh = cache_entry.get("timestamp", 0)
    now = time.time()
    if (
        cached_models
        and not force_refresh
        and now - last_refresh < GEMINI_CACHE_TTL
    ):
        return cached_models
    try:
        headers = {"x-goog-api-key": api_key}
        response = requests.get(GEMINI_MODELS_ENDPOINT, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        models = [
            model["name"].replace("models/", "")
            for model in data.get("models", [])
            if isinstance(model, dict) and "name" in model and model.get("supportedGenerationMethods", [])
        ]
        if models:
            cache_entry["models"] = models
            cache_entry["timestamp"] = now
            cache_entry["error"] = None
            return models
    except Exception as err:
        message = f"[LLM AIO] Failed to refresh Gemini models: {err}"
        print(message)
        cache_entry["error"] = message
    return cached_models


def get_gemini_models_error(api_key: Optional[str] = None) -> Optional[str]:
    if not api_key:
        return None
    cache_key = _hash_api_key(api_key)
    cache_entry = GEMINI_MODELS_CACHE.get(cache_key)
    if not cache_entry:
        return None
    return cache_entry.get("error")


def get_models_by_provider(
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    force_refresh_openai: bool = False,
    force_refresh_anthropic: bool = False,
    force_refresh_gemini: bool = False,
    force_refresh_openrouter: bool = False,
) -> Dict[str, List[str]]:
    return {
        "openai": get_openai_models(api_key=openai_api_key, force_refresh=force_refresh_openai),
        "anthropic": get_anthropic_models(api_key=anthropic_api_key, force_refresh=force_refresh_anthropic),
        "gemini": get_gemini_models(api_key=gemini_api_key, force_refresh=force_refresh_gemini),
        "openrouter": get_openrouter_models(force_refresh=force_refresh_openrouter),
    }


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def normalize_provider_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    lowered = name.lower()
    if lowered == "claude":
        return "anthropic"
    return lowered


def get_all_model_options() -> List[str]:
    seen = set()
    ordered = []

    # Get models from active API calls (OpenRouter models, which don't need keys)
    for provider_models in get_models_by_provider().values():
        for model in provider_models:
            if model not in seen:
                seen.add(model)
                ordered.append(model)

    # Also include any cached models from previous fetches
    # This ensures models fetched by the frontend are available for validation
    for cache_entry in OPENAI_MODELS_CACHE.values():
        for model in cache_entry.get("models", []):
            if model not in seen:
                seen.add(model)
                ordered.append(model)

    for cache_entry in ANTHROPIC_MODELS_CACHE.values():
        for model in cache_entry.get("models", []):
            if model not in seen:
                seen.add(model)
                ordered.append(model)

    for cache_entry in GEMINI_MODELS_CACHE.values():
        for model in cache_entry.get("models", []):
            if model not in seen:
                seen.add(model)
                ordered.append(model)

    return ordered

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
            content.insert(0, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image
                }
            })
        return cls(role=role, content=content)

    def to_openai_message(self):
        content = self.content
        if len(content) == 1 and content[0]["type"] == "text":
            return {
                "role": self.role,
                "content": content[0]["text"]
            }

        # Reformat content for OpenAI API
        openai_content = []
        for item in content:
            if item.get("type") == "image" and "source" in item:
                source = item["source"]
                if source.get("type") == "base64":
                    openai_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{source.get('media_type', 'image/png')};base64,{source.get('data', '')}",
                            "detail": "auto" # Default detail level
                        }
                    })
            elif item.get("type") == "text":
                openai_content.append(item)
            # Add handling for other types if necessary, or ignore them

        return {
            "role": self.role,
            "content": openai_content
        }

    def to_claude_message(self):
        return {
            "role": self.role,
            "content": self.content
        }

    def to_gemini_message(self):
        # Gemini uses "parts" array directly without role in the parts
        parts = []
        for item in self.content:
            if item.get("type") == "text":
                parts.append({"text": item["text"]})
            elif item.get("type") == "image" and "source" in item:
                source = item["source"]
                if source.get("type") == "base64":
                    parts.append({
                        "inline_data": {
                            "mime_type": source.get("media_type", "image/png"),
                            "data": source.get("data", "")
                        }
                    })
        return {"parts": parts}

class OpenAIApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://api.openai.com/v1"
    timeout: Optional[int] = 60

    def chat(self, messages: List[LLMMessage], config: LLMConfig, seed=None):
        available = get_openai_models(api_key=self.api_key)
        if available and config.model not in available:
            raise Exception(f"Must provide an OpenAI model, got {config.model}")
        formatted_messages = [m.to_openai_message() for m in messages]
        url = f"{self.endpoint}/chat/completions"
        data = {
            "messages": formatted_messages,
            "model": config.model,
            "max_tokens": config.max_token,
            "temperature": config.temperature,
        }
        if seed is not None:
            data["seed"] = seed
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
        data: Dict = response.json()
        if data.get("error", None) is not None:
            raise Exception(data.get("error").get("message"))
        return data["choices"][0]["message"]["content"]

    def complete(self, prompt: str, config: LLMConfig, seed=None):
        messages = [LLMMessage.create(role=LLMMessageRole.user, text=prompt)]
        return self.chat(messages, config, seed)

class OpenRouterApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://openrouter.ai/api/v1"
    timeout: Optional[int] = 60
    referer: str = OPENROUTER_DEFAULT_REFERER
    title: str = OPENROUTER_DEFAULT_APP_TITLE

    def chat(self, messages: List[LLMMessage], config: LLMConfig, seed=None):
        available = get_openrouter_models()
        if available and config.model not in available:
            raise Exception(f"Must provide an OpenRouter model, got {config.model}")
        formatted_messages = [m.to_openai_message() for m in messages]
        url = f"{self.endpoint}/chat/completions"
        data = {
            "messages": formatted_messages,
            "model": config.model,
            "max_tokens": config.max_token,
            "temperature": config.temperature,
        }
        if seed is not None:
            data["seed"] = seed
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.referer or OPENROUTER_DEFAULT_REFERER,
            "X-Title": self.title or OPENROUTER_DEFAULT_APP_TITLE,
        }
        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
        data: Dict = response.json()
        if data.get("error"):
            error_data = data.get("error")
            raise Exception(error_data.get("message", str(error_data)))
        return data["choices"][0]["message"]["content"]

    def complete(self, prompt: str, config: LLMConfig, seed=None):
        messages = [LLMMessage.create(role=LLMMessageRole.user, text=prompt)]
        return self.chat(messages, config, seed)

class ClaudeApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://api.anthropic.com/v1"
    version: Optional[str] = ANTHROPIC_DEFAULT_VERSION
    timeout: Optional[int] = 60

    def chat(self, messages: List[LLMMessage], config: LLMConfig):
        available = get_anthropic_models(api_key=self.api_key, version=self.version)
        if available and config.model not in available:
            raise Exception(f"Must provide an Anthropic model, got {config.model}")
        system_message = next((m for m in messages if m.role == LLMMessageRole.system), None)
        user_messages = [m for m in messages if m.role != LLMMessageRole.system]
        formatted_messages = [m.to_claude_message() for m in user_messages]
        url = f"{self.endpoint}/messages"
        data = {
            "messages": formatted_messages,
            "model": config.model,
            "max_tokens": config.max_token,
            "temperature": config.temperature,
        }
        if system_message:
            data["system"] = system_message.content[0]["text"]
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.version,
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
        data: Dict = response.json()
        if data.get("error", None) is not None:
            raise Exception(data.get("error").get("message"))
        return data["content"][0]["text"]

    def complete(self, prompt: str, config: LLMConfig):
        messages = [LLMMessage.create(role=LLMMessageRole.user, text=prompt)]
        return self.chat(messages, config)

class GeminiApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://generativelanguage.googleapis.com/v1beta"
    timeout: Optional[int] = 60

    def chat(self, messages: List[LLMMessage], config: LLMConfig):
        available = get_gemini_models(api_key=self.api_key)
        if available and config.model not in available:
            raise Exception(f"Must provide a Gemini model, got {config.model}")

        # Convert messages to Gemini format
        contents = [m.to_gemini_message() for m in messages]

        url = f"{self.endpoint}/models/{config.model}:generateContent"
        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_token,
            }
        }
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
        data: Dict = response.json()

        if data.get("error"):
            error_data = data.get("error")
            raise Exception(error_data.get("message", str(error_data)))

        if not data.get("candidates"):
            raise Exception("No response candidates returned from Gemini")

        return data["candidates"][0]["content"]["parts"][0]["text"]

    def complete(self, prompt: str, config: LLMConfig):
        messages = [LLMMessage.create(role=LLMMessageRole.user, text=prompt)]
        return self.chat(messages, config)

class AwsBedrockMistralApi(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: Optional[str] = None
    region: Optional[str] = aws_regions[0]
    timeout: Optional[int] = 60
    bedrock_runtime: Any = None

    def __init__(self, **data):
        super().__init__(**data)
        ensure_package("boto3", version="1.34.101")
        import boto3
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token,
            region_name=self.region,
        )

    def chat(self, messages: List[LLMMessage], config: LLMConfig):
        raise Exception("Mistral doesn't support chat API")

    def complete(self, prompt: str, config: LLMConfig):
        if config.model not in bedrock_mistral_models:
            raise Exception(f"Must provide a Mistral model, got {config.model}")
        prompt = f"<s>[INST]{prompt}[/INST]"
        data = {
            "prompt": prompt,
            "max_tokens": config.max_token,
            "temperature": config.temperature,
        }
        response = self.bedrock_runtime.invoke_model(body=json.dumps(data), modelId=config.model)
        data: Dict = json.loads(response.get("body").read())
        if data.get("error", None) is not None:
            raise Exception(data.get("error").get("message"))
        return data["outputs"][0]["text"]

class AwsBedrockClaudeApi(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: Optional[str] = None
    region: Optional[str] = aws_regions[0]
    version: Optional[str] = bedrock_anthropic_versions[0]
    timeout: Optional[int] = 60
    bedrock_runtime: Any = None

    def __init__(self, **data):
        super().__init__(**data)
        ensure_package("boto3", version="1.34.101")
        import boto3
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_session_token=self.aws_session_token,
            region_name=self.region,
        )

    def chat(self, messages: List[LLMMessage], config: LLMConfig):
        if config.model not in bedrock_claude3_models:
            raise Exception(f"Must provide a Claude v3 model, got {config.model}")
        system_message = next((m for m in messages if m.role == LLMMessageRole.system), None)
        user_messages = [m for m in messages if m.role != LLMMessageRole.system]
        formatted_messages = [m.to_claude_message() for m in user_messages]
        data = {
            "anthropic_version": self.version,
            "messages": formatted_messages,
            "max_tokens": config.max_token,
            "temperature": config.temperature,
        }
        if system_message:
            data["system"] = system_message.content[0]["text"]
        response = self.bedrock_runtime.invoke_model(body=json.dumps(data), modelId=config.model)
        data: Dict = json.loads(response.get("body").read())
        if data.get("error", None) is not None:
            raise Exception(data.get("error").get("message"))
        return data["content"][0]["text"]

    def complete(self, prompt: str, config: LLMConfig):
        if config.model not in bedrock_claude2_models:
            raise Exception(f"Must provide a Claude v2 model, got {config.model}")
        data = {
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": config.max_token,
            "temperature": config.temperature,
        }
        response = self.bedrock_runtime.invoke_model(body=json.dumps(data), modelId=config.model)
        data: Dict = json.loads(response.get("body").read())
        if data.get("error", None) is not None:
            raise Exception(data.get("error").get("message"))
        return data["completion"]

LLMApi = Union[OpenAIApi, ClaudeApi, GeminiApi, OpenRouterApi, AwsBedrockMistralApi, AwsBedrockClaudeApi]

class LLMAIONode:
    TITLE = "LLM All-In-One"
    CATEGORY = "oshtz Nodes"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)
    FUNCTION = "process"

    @classmethod
    def INPUT_TYPES(cls):
        model_values = get_all_model_options()
        default_model = model_values[0] if model_values else ""
        if not model_values:
            model_values = [""]
        return {
            "required": {
                "api_type": (["openai", "anthropic", "gemini", "openrouter"],),
                "model": (
                    model_values,
                    {"default": default_model},
                ),
                "max_token": ("INT", {"default": 1024, "min": 1, "max": 8192}),
                "temperature": ("FLOAT", {"default": 0, "min": 0, "max": 1.0, "step": 0.01}),
                "prompt": ("STRING", {"multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0x1FFFFFFFFFFFFF}),
            },
            "optional": {
                "openai_api_key": ("STRING", {"multiline": False}),
                "anthropic_api_key": ("STRING", {"multiline": False}),
                "gemini_api_key": ("STRING", {"multiline": False}),
                "openrouter_api_key": ("STRING", {"multiline": False}),
                "image": ("IMAGE",),
            }
        }

    def process(self, api_type, model, max_token, temperature, prompt, seed,
                openai_api_key=None, anthropic_api_key=None, gemini_api_key=None, openrouter_api_key=None,
                image: Optional[Tensor] = None):
        provider = normalize_provider_name(api_type)
        config = LLMConfig(
            model=model,
            max_token=max_token,
            temperature=temperature
        )

        if provider == "openai":
            if not openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI models")
            api = OpenAIApi(api_key=openai_api_key)
        elif provider == "anthropic":
            if not anthropic_api_key:
                raise ValueError("Anthropic API key is required for Anthropic models")
            api = ClaudeApi(api_key=anthropic_api_key)
        elif provider == "gemini":
            if not gemini_api_key:
                raise ValueError("Gemini API key is required for Gemini models")
            api = GeminiApi(api_key=gemini_api_key)
        elif provider == "openrouter":
            if not openrouter_api_key:
                raise ValueError("OpenRouter API key is required for OpenRouter models")
            api = OpenRouterApi(
                api_key=openrouter_api_key,
            )
        else:
            raise ValueError(f"Unsupported API type: {api_type}")

        if image is not None:
            pil = tensor2pil(image)
            image_content = pil2base64(pil)
            message = LLMMessage.create(role=LLMMessageRole.user, text=prompt, image=image_content)
        else:
            message = LLMMessage.create(role=LLMMessageRole.user, text=prompt)

        if provider == "openai":
            response = api.chat([message], config, seed=seed)
        elif provider == "openrouter":
            response = api.chat([message], config, seed=seed)
        else:
            response = api.chat([message], config)
        return (response,)

NODE_CLASS_MAPPINGS = {
    "LLMAIONode": LLMAIONode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LLMAIONode": "LLM All-In-One"
}

if server and web:
    def _build_model_response(
        provider: Optional[str],
        force_refresh: bool,
        openai_api_key: Optional[str],
        anthropic_api_key: Optional[str],
        gemini_api_key: Optional[str],
    ):
        normalized = normalize_provider_name(provider)
        if normalized == "openrouter":
            models = get_openrouter_models(force_refresh=force_refresh)
            return {"provider": normalized, "models": models}
        if normalized == "openai":
            models = get_openai_models(api_key=openai_api_key, force_refresh=force_refresh)
            error = get_openai_models_error(api_key=openai_api_key)
            return {"provider": normalized, "models": models, "error": error}
        if normalized == "anthropic":
            models = get_anthropic_models(api_key=anthropic_api_key, force_refresh=force_refresh)
            error = get_anthropic_models_error(api_key=anthropic_api_key)
            return {"provider": normalized, "models": models, "error": error}
        if normalized == "gemini":
            models = get_gemini_models(api_key=gemini_api_key, force_refresh=force_refresh)
            error = get_gemini_models_error(api_key=gemini_api_key)
            return {"provider": normalized, "models": models, "error": error}
        if normalized:
            models = get_models_by_provider(
                openai_api_key=openai_api_key,
                anthropic_api_key=anthropic_api_key,
                gemini_api_key=gemini_api_key,
                force_refresh_openai=force_refresh,
                force_refresh_anthropic=force_refresh,
                force_refresh_gemini=force_refresh,
                force_refresh_openrouter=force_refresh,
            ).get(normalized, [])
            return {"provider": normalized, "models": models}
        return get_models_by_provider(
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key,
            gemini_api_key=gemini_api_key,
            force_refresh_openai=force_refresh,
            force_refresh_anthropic=force_refresh,
            force_refresh_gemini=force_refresh,
            force_refresh_openrouter=force_refresh,
        )

    @server.PromptServer.instance.routes.get("/oshtz-nodes/llm-models")
    async def get_llm_models(request):
        provider = request.rel_url.query.get("provider")
        force_refresh = _truthy(request.rel_url.query.get("force", "0"))
        openai_api_key = request.rel_url.query.get("openai_api_key")
        anthropic_api_key = request.rel_url.query.get("anthropic_api_key")
        gemini_api_key = request.rel_url.query.get("gemini_api_key")
        data = _build_model_response(provider, force_refresh, openai_api_key, anthropic_api_key, gemini_api_key)
        return web.json_response(data)

    @server.PromptServer.instance.routes.post("/oshtz-nodes/llm-models")
    async def post_llm_models(request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        provider = payload.get("provider")
        force_refresh = _truthy(payload.get("force", False))
        openai_api_key = payload.get("openai_api_key")
        anthropic_api_key = payload.get("anthropic_api_key")
        gemini_api_key = payload.get("gemini_api_key")
        data = _build_model_response(provider, force_refresh, openai_api_key, anthropic_api_key, gemini_api_key)
        return web.json_response(data)
