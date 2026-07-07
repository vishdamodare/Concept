import os
import uuid
import logging
import asyncio
import random
from typing import List, Optional, Tuple, Dict, Any
import httpx
import litellm

log = logging.getLogger("conceptforge.llm")

# Normalize LiteLLM / OpenAI proxy base URLs to avoid duplicated "/v1" path
# e.g. if a user sets LITELLM_API_BASE="https://api.emergent.sh/v1" we convert it
# to "https://api.emergent.sh" so downstream clients don't produce "/v1/v1/...".
for env_key in ("LITELLM_API_BASE", "OPENAI_API_BASE", "EMERGENT_API_BASE"):
    raw = os.environ.get(env_key)
    if raw:
        normalized = raw.rstrip('/')
        if normalized.endswith('/v1'):
            normalized = normalized[:-3]
        os.environ[env_key] = normalized
        log.info(f"Normalized {env_key} -> {normalized}")

class UserMessage:
    """Wrapper for user message content."""
    def __init__(self, text: str):
        self.text = text

class LlmChat:
    """Dynamic LlmChat manager routing completions directly to Google Gemini."""
    def __init__(self, api_key: str, session_id: str, system_message: str):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.provider = "gemini"
        self.model = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
        self.params = {}

    def with_model(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        return self

    def with_params(self, **kwargs):
        self.params.update(kwargs)
        return self

    def _get_api_setup(self) -> Tuple[str, str, Optional[str]]:
        # Keep GOOGLE_API_KEY / GEMINI_API_KEY fallback
        api_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        # Allow an explicit litellm/openai API base to be set via environment variables.
        api_base = os.environ.get("LITELLM_API_BASE") or os.environ.get("OPENAI_API_BASE") or os.environ.get("EMERGENT_API_BASE") or None
        model_name = self.model
        provider = self.provider

        # Map non-Gemini models to default Gemini model
        if "gemini" not in model_name.lower() and provider != "gemini":
            model_name = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
            provider = "gemini"

        # Direct Gemini API prefix normalization
        if not model_name.startswith("gemini/"):
            model_name = f"gemini/{model_name}"

        return model_name, api_key, api_base

    async def _execute_with_retry(self, func, *args, **kwargs):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                status_code = getattr(e, "status_code", None)

                # Identify permanent non-retryable errors
                is_permanent = (
                    status_code in (400, 401, 403) or 
                    any(x in err_str for x in ["401", "403", "400", "invalid key", "invalid_api_key", "bad request", "unauthorized"])
                )

                # Check for retryable errors (429, 503, 504, timeout, connection)
                is_retryable = (
                    status_code in (429, 503, 504) or
                    any(x in err_str for x in ["ratelimit", "429", "quota", "limit", "503", "504", "timeout", "connection"])
                )

                if is_retryable and not is_permanent and attempt < max_retries - 1:
                    sleep_time = min((2 ** attempt) + random.uniform(0, 1), 30)
                    log.warning(f"LLM retryable error hit (attempt {attempt + 1}/{max_retries}). Retrying in {sleep_time:.2f}s... Error: {e}")
                    await asyncio.sleep(sleep_time)
                else:
                    raise

    async def send_message(self, message: UserMessage) -> str:
        model_name, api_key, api_base = self._get_api_setup()
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": message.text}
        ]
        log.info(f"Sending message to {model_name} via LiteLLM (api_base={api_base or 'default'})")
        try:
            call_kwargs = {"model": model_name, "messages": messages, "api_key": api_key, "timeout": 60}
            # Merge in optional api_base if provided by the environment
            if api_base:
                call_kwargs["api_base"] = api_base
            # Merge user-supplied params (e.g. response_format)
            call_kwargs.update(self.params)

            response = await self._execute_with_retry(
                litellm.acompletion,
                **call_kwargs
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            log.error(f"Error calling litellm completions: {e}")
            raise

    async def send_message_multimodal_response(self, message: UserMessage) -> Tuple[str, List[Dict[str, Any]]]:
        model_name, api_key, api_base = self._get_api_setup()
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": message.text}
        ]

        text_content = ""
        images = []
        raw_response = {}

        log.info(f"Sending multimodal message to {model_name} via LiteLLM (api_base={api_base or 'default'})")
        try:
            call_kwargs = {"model": model_name, "messages": messages, "api_key": api_key, "timeout": 60}
            if api_base:
                call_kwargs["api_base"] = api_base
            call_kwargs.update(self.params)

            response = await self._execute_with_retry(
                litellm.acompletion,
                **call_kwargs
            )
            if response.choices:
                message_obj = response.choices[0].message
                text_content = message_obj.content or ""
                raw_response = response.dict() if hasattr(response, 'dict') else dict(response)
                images = self._find_images(raw_response)
        except Exception as e:
            log.error(f"Error calling litellm multimodal completions: {e}")
            raise

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
