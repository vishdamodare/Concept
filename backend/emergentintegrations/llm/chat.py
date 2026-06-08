import os
import uuid
import logging
import asyncio
from typing import List, Optional, Tuple, Dict, Any
import httpx
import litellm

log = logging.getLogger("conceptforge.emergent")

class UserMessage:
    """Wrapper for user message content."""
    def __init__(self, text: str):
        self.text = text

class LlmChat:
    """Replacement for LlmChat routing requests via direct httpx or litellm to the platform LLM proxy or direct providers."""
    def __init__(self, api_key: str, session_id: str, system_message: str):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.provider = "anthropic"
        self.model = os.environ.get("LLM_MODEL") or "claude-sonnet-4-6"
        self.params = {}

    def with_model(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        return self

    def with_params(self, **kwargs):
        self.params.update(kwargs)
        return self

    def _get_api_setup(self) -> Tuple[Optional[str], str, bool, str]:
        # Resolve api_base
        api_base = os.environ.get("LITELLM_API_BASE") or os.environ.get("OPENAI_API_BASE") or "https://api.emergent.sh"
        
        # Check if we have a direct Google/Gemini key set
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        # Resolve model name and provider
        model_name = self.model
        provider = self.provider
        
        # If gemini_key is set, we route everything to Google Gemini directly
        if gemini_key:
            # If the requested model is not already a Gemini model, map it to gemini-2.0-flash
            if "gemini" not in model_name.lower() and provider != "gemini":
                model_name = os.environ.get("LLM_MODEL") or "gemini-2.0-flash"
                provider = "gemini"
            
            # Ensure model name starts with "gemini/" for LiteLLM routing
            if not model_name.startswith("gemini/"):
                model_name = f"gemini/{model_name}"
                
            # Direct LiteLLM call to Google Gemini (no proxy)
            return None, model_name, False, gemini_key
            
        # If no gemini_key is set, use the emergent platform proxy
        if provider and "/" not in model_name:
            model_name = f"{provider}/{model_name}"
            
        use_direct_proxy = "emergent.sh" in api_base
        return api_base, model_name, use_direct_proxy, self.api_key

    async def _send_direct_proxy_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        api_base, _, _, target_api_key = self._get_api_setup()
        if not api_base:
            api_base = "https://api.emergent.sh"
        
        # Strip trailing slashes and append the exact OpenAI chat completions path
        base_url = api_base.rstrip("/")
        if not base_url.endswith("/v1"):
            url = f"{base_url}/v1/chat/completions"
        else:
            url = f"{base_url}/chat/completions"
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {target_api_key}"
        }
        
        # The platform proxy maps direct model names (like claude-sonnet-4-6)
        data = {
            "model": self.model,
            "messages": messages,
            **self.params
        }
        
        log.info(f"Sending direct HTTP completions request to: {url} (model: {self.model})")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data, timeout=120.0)
            if response.status_code != 200:
                log.error(f"Proxy request failed with status {response.status_code}: {response.text}")
                raise Exception(f"Proxy error ({response.status_code}): {response.text}")
            return response.json()

    async def _execute_with_retry(self, func, *args, **kwargs):
        max_retries = 5
        delay = 2.0
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Check if this is a rate limit or quota error (429/quota exceeded)
                is_rate_limit = False
                err_str = str(e).lower()
                if "ratelimit" in err_str or "429" in err_str or "quota" in err_str or "limit" in err_str:
                    is_rate_limit = True
                
                if is_rate_limit and attempt < max_retries - 1:
                    log.warning(f"LLM rate limit or quota hit (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s... Error: {e}")
                    await asyncio.sleep(delay)
                    delay *= 2.0  # exponential backoff
                else:
                    raise

    async def send_message(self, message: UserMessage) -> str:
        api_base, model_name, use_direct_proxy, target_api_key = self._get_api_setup()
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": message.text}
        ]
        
        if use_direct_proxy:
            # Route default proxy calls directly via httpx
            try:
                response_json = await self._execute_with_retry(self._send_direct_proxy_request, messages)
                return response_json["choices"][0]["message"]["content"] or ""
            except Exception as e:
                log.error(f"Error calling direct completions: {e}")
                raise
        else:
            # Fallback to standard LiteLLM (passes None to api_base if it is the default proxy, letting LiteLLM call Google directly)
            log.info(f"Sending message to {model_name} via LiteLLM to {api_base or 'default endpoint'}")
            try:
                response = await self._execute_with_retry(
                    litellm.acompletion,
                    model=model_name,
                    messages=messages,
                    api_key=target_api_key,
                    api_base=api_base,
                    **self.params
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                log.error(f"Error calling litellm completions: {e}")
                raise

    async def send_message_multimodal_response(self, message: UserMessage) -> Tuple[str, List[Dict[str, Any]]]:
        api_base, model_name, use_direct_proxy, target_api_key = self._get_api_setup()
        
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": message.text}
        ]
        
        text_content = ""
        images = []
        raw_response = {}
        
        if use_direct_proxy:
            log.info(f"Sending direct multimodal completions request to: {api_base}")
            try:
                raw_response = await self._execute_with_retry(self._send_direct_proxy_request, messages)
                if raw_response.get("choices"):
                    message_obj = raw_response["choices"][0]["message"]
                    text_content = message_obj.get("content") or ""
            except Exception as e:
                log.error(f"Error calling direct multimodal completions: {e}")
                raise
        else:
            # Fallback to standard LiteLLM
            log.info(f"Sending multimodal message to {model_name} via LiteLLM to {api_base or 'default endpoint'}")
            try:
                response = await self._execute_with_retry(
                    litellm.acompletion,
                    model=model_name,
                    messages=messages,
                    api_key=target_api_key,
                    api_base=api_base,
                    **self.params
                )
                if response.choices:
                    message_obj = response.choices[0].message
                    text_content = message_obj.content or ""
                    raw_response = response.dict() if hasattr(response, 'dict') else dict(response)
            except Exception as e:
                log.error(f"Error calling litellm multimodal completions: {e}")
                raise

        # Extract images from response dict
        if raw_response:
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
