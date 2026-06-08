import os
import uuid
import logging
from typing import List, Optional, Tuple, Dict, Any
import litellm

log = logging.getLogger("conceptforge.emergent")

class UserMessage:
    """Wrapper for user message content."""
    def __init__(self, text: str):
        self.text = text

class LlmChat:
    """Mock/Replacement for LlmChat routing requests via litellm to the platform LLM proxy."""
    def __init__(self, api_key: str, session_id: str, system_message: str):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.provider = "anthropic"
        self.model = os.environ.get("LLM_MODEL") or "claude-3-5-sonnet-20241022"
        self.params = {}

    def with_model(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        return self

    def with_params(self, **kwargs):
        self.params.update(kwargs)
        return self

    def _get_api_setup(self) -> Tuple[str, str]:
        # Resolve api_base
        api_base = os.environ.get("LITELLM_API_BASE") or os.environ.get("OPENAI_API_BASE") or "https://api.emergent.sh/v1"
        
        # Always use 'openai/' prefix to force LiteLLM to call the OpenAI-compatible 
        # /v1/chat/completions endpoint on the custom proxy (which doesn't implement /v1/messages).
        model_name = self.model
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
        model_name = f"openai/{model_name}"
        
        return api_base, model_name

    async def send_message(self, message: UserMessage) -> str:
        api_base, model_name = self._get_api_setup()
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": message.text}
        ]
        
        log.info(f"Sending message to {model_name} via {api_base}")
        try:
            response = await litellm.acompletion(
                model=model_name,
                messages=messages,
                api_key=self.api_key,
                api_base=api_base,
                **self.params
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            log.error(f"Error calling completions: {e}")
            raise

    async def send_message_multimodal_response(self, message: UserMessage) -> Tuple[str, List[Dict[str, Any]]]:
        api_base, model_name = self._get_api_setup()
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": message.text}
        ]
        
        log.info(f"Sending multimodal message to {model_name} via {api_base}")
        try:
            response = await litellm.acompletion(
                model=model_name,
                messages=messages,
                api_key=self.api_key,
                api_base=api_base,
                **self.params
            )
        except Exception as e:
            log.error(f"Error calling multimodal completions: {e}")
            raise

        text_content = ""
        images = []
        
        if response.choices:
            message_obj = response.choices[0].message
            text_content = message_obj.content or ""
            
            # Recursively find any base64 image data in response dict
            raw_response = response.dict() if hasattr(response, 'dict') else dict(response)
            images = self._find_images(raw_response)
            
        # Fallback if no images found but we expected image modality
        if not images and "image" in self.params.get("modalities", []):
            log.warning("No image data found in response, using placeholder")
            # 1x1 transparent PNG placeholder
            placeholder = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            images = [{"mime_type": "image/png", "data": placeholder}]
            
        return text_content, images

    def _find_images(self, data: Any) -> List[Dict[str, Any]]:
        images = []
        if isinstance(data, dict):
            if 'data' in data and ('mime_type' in data or 'mimeType' in data):
                mime = data.get('mime_type') or data.get('mimeType')
                images.append({
                    "mime_type": mime,
                    "data": data['data']
                })
            else:
                for v in data.values():
                    images.extend(self._find_images(v))
        elif isinstance(data, list):
            for item in data:
                images.extend(self._find_images(item))
        return images
