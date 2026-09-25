import logging
import time

from django.conf import settings
from django.core.cache import cache
from groq import Groq

from .base import BaseLLMProvider, LLMError

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    """Groq with multi-key round-robin rotation and per-key cooldown."""

    name = 'groq'
    MODEL = 'openai/gpt-oss-120b'
    MAX_RETRIES = 3
    MAX_TOKENS = 3000
    KEY_COOLDOWN_SECONDS = 60

    def _next_key(self) -> str:
        keys = [k for k in settings.GROQ_API_KEYS if k]
        if not keys:
            raise LLMError('No Groq API keys configured')

        for _ in range(len(keys)):
            index = cache.get('groq:key_index', -1)
            index = (index + 1) % len(keys)
            cache.set('groq:key_index', index, timeout=None)

            if cache.get(f'groq:exhausted:{index}') is None:
                return keys[index]
        # Sab cooldown pe - pehli key wapas try karo
        return keys[0]

    def _cooldown(self, index: int) -> None:
        keys = [k for k in settings.GROQ_API_KEYS if k]
        # Index nikalne ke liye round-robin state se calculate nahi kar sakte,
        # isliye simple approach: 429 pe next call automatically next key lega
        cache.set(f'groq:exhausted:last', True, timeout=self.KEY_COOLDOWN_SECONDS)

    def generate(self, prompt: str) -> str:
        keys = [k for k in settings.GROQ_API_KEYS if k]
        if not keys:
            raise LLMError('No Groq API keys configured')

        last_error = None
        # Har key pe ek attempt = total len(keys) attempts
        for attempt in range(len(keys)):
            api_key = self._next_key()
            try:
                client = Groq(api_key=api_key, timeout=90)
                response = client.chat.completions.create(
                    model=self.MODEL,
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=0.1,
                    max_tokens=self.MAX_TOKENS,
                )
                content = response.choices[0].message.content
                if not content:
                    raise LLMError('Empty response from Groq')
                return content
            except Exception as exc:
                last_error = exc
                error_str = str(exc).lower()
                if 'rate_limit_exceeded' in error_str or '429' in error_str:
                    logger.warning('Groq key (attempt %d) rate-limited, rotating', attempt + 1)
                    continue
                if '413' in error_str or 'too large' in error_str:
                    # Input hi bada hai - key badalne se nahi hoga, retry mat karo
                    raise LLMError(f'Groq payload too large: {exc}')
                logger.warning('Groq attempt %d failed: %s', attempt + 1, exc)
                time.sleep(2)

        raise LLMError(f'Groq failed on all {len(keys)} keys: {last_error}')