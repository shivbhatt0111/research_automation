import logging
import time

from django.conf import settings
from django.core.cache import cache
from groq import Groq

from .base import BaseLLMProvider, LLMError

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    """Groq provider with multi-key round-robin rotation and stable model."""

    name = 'groq'
    # FIXED: Using the most stable and powerful Groq model for JSON extraction
    # MODEL = 'llama-3.3-70b-versatile' 
    MODEL = 'openai/gpt-oss-120b'
    MAX_RETRIES = 2 
    MAX_TOKENS = 4000
    KEY_COOLDOWN_SECONDS = 60

    def _get_keys(self) -> list[str]:
        return [k for k in getattr(settings, 'GROQ_API_KEYS', []) if k]

    def generate(self, prompt: str) -> str:
        keys = self._get_keys()
        if not keys:
            raise LLMError('No Groq API keys configured')

        last_error = None
        
        for attempt in range(len(keys)):
            index = cache.get('groq:key_index', -1)
            index = (index + 1) % len(keys)
            cache.set('groq:key_index', index, timeout=None)
            
            # Skip if this specific key is on cooldown
            if cache.get(f'groq:exhausted:{index}') is not None:
                continue

            api_key = keys[index]
            try:
                client = Groq(api_key=api_key, timeout=90)
                
                # Added tool_choice="none" implicitly by not passing tools, 
                # but using a stable model prevents hallucinated tool calls.
                response = client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {'role': 'system', 'content': 'You are a strict data extraction assistant. Respond ONLY with valid JSON. Do not attempt to use any web search or external tools.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    temperature=0.1,
                    max_tokens=self.MAX_TOKENS,
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise LLMError('Empty response from Groq')
                    
                return content.strip()
                
            except Exception as exc:
                last_error = exc
                error_str = str(exc).lower()
                
                # Handle Rate Limit
                if 'rate_limit_exceeded' in error_str or '429' in error_str:
                    logger.warning('Groq key #%d rate-limited, cooling down for 60s', index + 1)
                    cache.set(f'groq:exhausted:{index}', True, timeout=self.KEY_COOLDOWN_SECONDS)
                    continue
                
                # Handle Tool Call Hallucination (400 Error)
                if 'tool' in error_str and '400' in error_str:
                    logger.warning('Groq model hallucinated a tool call. Retrying with next key...')
                    continue
                    
                # Handle Payload Too Large
                if '413' in error_str or 'too large' in error_str:
                    raise LLMError(f'Groq payload too large: {exc}')
                    
                logger.warning('Groq attempt %d failed: %s', attempt + 1, exc)
                time.sleep(1)

        raise LLMError(f'Groq failed on all {len(keys)} keys: {last_error}')