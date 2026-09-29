import logging
import time

from django.conf import settings

import requests

from .base import BaseLLMProvider, LLMError

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter free-models pool. Daily limits reset every day.
    Rotates through multiple free models - one exhausted, next is tried."""

    name = 'openrouter'
    FREE_MODELS = [
        'meta-llama/llama-3.3-70b-instruct:free',
        'qwen/qwen-2.5-72b-instruct:free',
        'deepseek/deepseek-chat-v3-0324:free',
        'google/gemma-3-27b-it:free',
    ]
    TIMEOUT = 90

    def generate(self, prompt: str) -> str:
        if not settings.OPENROUTER_API_KEY:
            raise LLMError('No OpenRouter API key configured')

        headers = {
            'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
        }

        last_error = None
        for model in self.FREE_MODELS:
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
                    logger.warning('OpenRouter %s rate-limited, trying next model', model)
                    last_error = f'{model}: 429'
                    continue

                resp.raise_for_status()
                content = resp.json()['choices'][0]['message']['content']
                if not content:
                    raise LLMError('Empty response from OpenRouter')
                return content

            except Exception as exc:
                logger.warning('OpenRouter %s failed: %s', model, exc)
                last_error = f'{model}: {exc}'
                continue

        raise LLMError(f'All OpenRouter free models failed: {last_error}')  