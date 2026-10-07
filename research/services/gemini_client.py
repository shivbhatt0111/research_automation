import logging
import re

from django.conf import settings
from django.core.cache import cache
from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)

RETRY_DELAY_PATTERN = re.compile(r'retryDelay["\']?\s*[:=]\s*["\']?(\d+)s')


class GeminiClientError(Exception):
    """Custom exception for Gemini client failures."""
    pass


class GeminiClient:
    """
    Multi-key + multi-model client with strict cooldown management.
    Ensures Celery workers never block and keys rotate seamlessly on 429 errors.
    """
    
    KEY_COOLDOWN_SECONDS = 60
    MAX_COOLDOWN_SECONDS = 30 * 60

    def __init__(self):
        # Filter out any empty keys just in case
        self.api_keys = [k for k in settings.GEMINI_API_KEYS if k]
        self.models = [settings.GEMINI_MODEL_ID, settings.GEMINI_BACKUP_MODEL_ID]
        
        if not self.api_keys:
            raise GeminiClientError("No valid Gemini API keys configured in settings.")


    
    def _next_available_key(self) -> tuple[int, str]:
        """Returns the next available key index and key string using round-robin."""
        for attempt in range(len(self.api_keys)):
            index = cache.get('gemini:key_index', -1)
            index = (index + 1) % len(self.api_keys)
            cache.set('gemini:key_index', index, timeout=None)

            # === DEBUG LOG ADD KAREIN ===
            logger.info(f"[DEBUG] Trying key #{index + 1} (attempt {attempt + 1}/{len(self.api_keys)})")
            logger.info(f"[DEBUG] Key status: exhausted={cache.get(f'gemini:exhausted:{index}')}")
            # ============================

            if cache.get(f'gemini:exhausted:{index}') is None:
                logger.info(f"[DEBUG] ✓ Using key #{index + 1}")
                return index, self.api_keys[index]

        logger.error(f"[DEBUG]  ALL {len(self.api_keys)} KEYS EXHAUSTED!")
        raise GeminiClientError('ALL_KEYS_COOLDOWN')
    
    
    

    def _cooldown_key(self, index: int, seconds: int) -> None:
        """Puts a specific key on cooldown in Redis cache."""
        seconds = min(seconds, self.MAX_COOLDOWN_SECONDS)
        cache.set(f'gemini:exhausted:{index}', True, timeout=seconds)
        logger.warning('Gemini key #%d put on cooldown for %ds', index + 1, seconds)

    @staticmethod
    def _error_code(exc: Exception) -> int | None:
        code = getattr(exc, 'code', None)
        return code if isinstance(code, int) else None

    @classmethod
    def _quota_retry_delay(cls, exc: Exception) -> int:
        """Extracts retry delay from Gemini error message, defaults to 60s."""
        match = RETRY_DELAY_PATTERN.search(str(exc))
        if match:
            return int(match.group(1))
        return cls.KEY_COOLDOWN_SECONDS

    def _invoke(self, client, model_id: str, prompt: str, use_search: bool, require_search: bool = False):
        """Handles the actual API call, with fallback if grounding fails."""
        if not use_search:
            return client.models.generate_content(model=model_id, contents=prompt)

        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
            return client.models.generate_content(
                model=model_id, contents=prompt, config=config,
            )
        except errors.APIError as exc:
            code = self._error_code(exc)
            # 400/404 often means the model doesn't support grounding or it's restricted
            if code == 429 or code in (400, 404):
                if require_search:
                    raise  # Bubble up the error if search is strictly required
                logger.warning('Grounding unavailable on %s (%s), degrading to plain call', model_id, code)
                return client.models.generate_content(model=model_id, contents=prompt)
            raise
        

    def generate(self, prompt: str, use_search: bool = False, require_search: bool = False) -> str:
        last_error: Exception | None = None
        all_rate_limited = True

        for model_id in self.models:
            for _ in range(len(self.api_keys)):
                try:
                    key_index, api_key = self._next_available_key()
                except GeminiClientError:
                    break 

                try:
                    client = genai.Client(
                        api_key=api_key,
                        http_options=types.HttpOptions(timeout=60_000),
                    )
                                    
                    
                    response = self._invoke(client, model_id, prompt, use_search, require_search)
                    
                    logger.info('Gemini call succeeded: model=%s key=#%d search=%s', model_id, key_index + 1, use_search)
                    return response.text

                except errors.APIError as exc:
                    last_error = exc
                    code = self._error_code(exc)

                    if code == 429:
                        
                        import time
                        wait_time = 5 
                        logger.warning(f'Rate limit hit on Key #{key_index+1}. Waiting {wait_time}s before next attempt...')
                        time.sleep(wait_time)
                        
                        
                        self._cooldown_key(key_index, self._quota_retry_delay(exc))
                        continue

                    all_rate_limited = False

                    if code in (400, 404):
                        logger.warning('Model %s or grounding unavailable (%s), falling back', model_id, code)
                        break 

                    logger.error('Gemini API error (%s): %s', code, exc)
                    continue

                except Exception as exc:
                    last_error = exc
                    all_rate_limited = False
                    logger.error('Gemini transient error: %s', exc)
                    continue

        if all_rate_limited:
            raise GeminiClientError('All Gemini keys quota-exhausted. Check rate limits.')
        
        raise GeminiClientError(f'All Gemini keys and models failed: {last_error}')