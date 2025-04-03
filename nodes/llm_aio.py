import os
import json
import requests
import random
from enum import Enum
from typing import List, Dict, Union, Optional, Any
import torch
from torch import Tensor
from pydantic import BaseModel
from PIL import Image
import base64
import io
from ..utils import ensure_package, tensor2pil, pil2base64

# Constants and model lists
gpt_models = [
    "gpt-3.5-turbo", "gpt-3.5-turbo-0125", "gpt-4o", "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06", "gpt-4o-mini", "gpt-4o-mini-2024-07-18", "gpt-4-turbo",
    "gpt-4-turbo-2024-04-09", "gpt-4-turbo-preview", "gpt-4-0125-preview",
    "gpt-4-1106-preview", "gpt-4-0613", "gpt-4", "o1-preview", "o1-mini",
]
gpt_vision_models = ["gpt-4o", "gpt-4o-2024-05-13", "gpt-4o-2024-08-06", "gpt-4o-mini", "gpt-4o-mini-2024-07-18", "gpt-4-turbo", "gpt-4-turbo-2024-04-09", "gpt-4-turbo-preview"]
claude3_models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-5-sonnet-20240620"]
claude2_models = ["claude-2.1"]
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

class OpenAIApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://api.openai.com/v1"
    timeout: Optional[int] = 60

    def chat(self, messages: List[LLMMessage], config: LLMConfig, seed=None):
        if config.model not in gpt_models:
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

class ClaudeApi(BaseModel):
    api_key: str
    endpoint: Optional[str] = "https://api.anthropic.com/v1"
    version: Optional[str] = "2023-06-01"
    timeout: Optional[int] = 60

    def chat(self, messages: List[LLMMessage], config: LLMConfig):
        if config.model not in claude3_models + claude2_models:
            raise Exception(f"Must provide a Claude model, got {config.model}")
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

LLMApi = Union[OpenAIApi, ClaudeApi, AwsBedrockMistralApi, AwsBedrockClaudeApi]

class LLMAIONode:
    TITLE = "LLM All-In-One"
    CATEGORY = "oshtz Nodes"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("response",)
    FUNCTION = "process"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_type": (["openai", "claude"],),
                "model": (
                    gpt_models
                    + claude3_models
                    + claude2_models,
                    {"default": gpt_vision_models[0]},
                ),
                "max_token": ("INT", {"default": 1024, "min": 1, "max": 8192}),
                "temperature": ("FLOAT", {"default": 0, "min": 0, "max": 1.0, "step": 0.01}),
                "prompt": ("STRING", {"multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0x1FFFFFFFFFFFFF}),
            },
            "optional": {
                "openai_api_key": ("STRING", {"multiline": False}),
                "anthropic_api_key": ("STRING", {"multiline": False}),
                "image": ("IMAGE",),
            }
        }

    def process(self, api_type, model, max_token, temperature, prompt, seed,
                openai_api_key=None, anthropic_api_key=None, image: Optional[Tensor] = None):
        config = LLMConfig(
            model=model,
            max_token=max_token,
            temperature=temperature
        )

        if api_type == "openai":
            if not openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI models")
            api = OpenAIApi(api_key=openai_api_key)
        elif api_type == "claude":
            if not anthropic_api_key:
                raise ValueError("Anthropic API key is required for Claude models")
            api = ClaudeApi(api_key=anthropic_api_key)
        else:
            raise ValueError(f"Unsupported API type: {api_type}")

        if image is not None:
            pil = tensor2pil(image)
            image_content = pil2base64(pil)
            message = LLMMessage.create(role=LLMMessageRole.user, text=prompt, image=image_content)
        else:
            message = LLMMessage.create(role=LLMMessageRole.user, text=prompt)

        if api_type == "openai":
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
