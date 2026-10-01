import logging
import time

from django.conf import settings
from django.core.cache import cache

import requests

from .base import BaseLLMProvider, LLMError

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter with multi-key rotation + multi-model fallback."""

    name = 'openrouter'
    FREE_MODELS = [
        'meta-llama/llama-3.3-70b-instruct:free',
        'qwen/qwen-2.5-72b-instruct:free',
        'deepseek/deepseek-chat-v3-0324:free',
        'google/gemma-3-27b-it:free',
    ]
    TIMEOUT = 90

    def _keys(self) -> list[str]:
        keys = [k for k in getattr(settings, 'OPENROUTER_API_KEYS', []) if k]
        if not keys:
            raise LLMError('No OpenRouter API keys configured')
        return keys

    def _next_key(self) -> str:
        keys = self._keys()
        for _ in range(len(keys)):
            index = cache.get('openrouter:key_index', -1)
            index = (index + 1) % len(keys)
            cache.set('openrouter:key_index', index, timeout=None)
            if cache.get(f'openrouter:exhausted:{index}') is None:
                return keys[index]
        return keys[0]

    def _cooldown_last(self) -> None:
        index = cache.get('openrouter:key_index', -1)
        if index >= 0:
            cache.set(f'openrouter:exhausted:{index}', True, timeout=3600)
            logger.warning('OpenRouter key #%d cooldown 1h (daily limit)', index + 1)

    def generate(self, prompt: str) -> str:
        keys = self._keys()
        headers_base = {'Content-Type': 'application/json'}

        last_error = None
        # Har key pe saare free models try (key rotation + model rotation)
        for model in self.FREE_MODELS:
            for attempt in range(len(keys)):
                api_key = self._next_key()
                headers = dict(headers_base, Authorization=f'Bearer {api_key}')
                try:
                    resp = requests.post(
                        'https://openrouter.ai/api/v1/chat/completions',
                        headers=headers,
                        json={
                            'model': model,
                            'messages': [{'role': 'user', 'content': prompt}],
                            'temperature': 0.1,
                            'max_tokens': 3000,
                        },
                        timeout=self.TIMEOUT,
                    )

                    if resp.status_code == 429:
                        # Is model pe daily limit - cooldown + agla model
                        self._cooldown_last()
                        last_error = f'{model}: 429'
                        logger.warning('OpenRouter %s rate-limited, next model', model)
                        break  # is model se aage nahi, next model

                    resp.raise_for_status()
                    content = resp.json()['choices'][0]['message']['content']
                    if not content:
                        raise LLMError('Empty response from OpenRouter')
                    logger.info('OpenRouter succeeded via %s', model)
                    return content

                except LLMError:
                    raise
                except Exception as exc:
                    last_error = f'{model}: {exc}'
                    logger.warning('OpenRouter %s attempt failed: %s', model, exc)
                    time.sleep(1)
                    continue

        raise LLMError(f'All OpenRouter keys/models failed: {last_error}')