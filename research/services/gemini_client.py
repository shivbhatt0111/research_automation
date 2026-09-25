import logging
import re
import time

from django.conf import settings
from django.core.cache import cache
from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)

RETRY_DELAY_PATTERN = re.compile(r'retryDelay["\']?\s*[:=]\s*["\']?(\d+)s')


class GeminiClientError(Exception):
    pass


class GeminiClient:
    """Multi-key + multi-model client. Waits out cooldowns instead of failing."""

    KEY_COOLDOWN_SECONDS = 60
    MAX_COOLDOWN_SECONDS = 30 * 60
    TOOL_REJECTED_CODES = (400, 404)
    KEY_WAIT_SECONDS = 90

    def __init__(self):
        self.api_keys = settings.GEMINI_API_KEYS
        self.models = [settings.GEMINI_MODEL_ID, settings.GEMINI_BACKUP_MODEL_ID]

    def _next_available_key(self) -> tuple[int, str]:
        """Waits for a cooldown to expire. Raises only after KEY_WAIT_SECONDS."""
        deadline = time.time() + self.KEY_WAIT_SECONDS

        while True:
            for _ in range(len(self.api_keys)):
                index = cache.get('gemini:key_index', -1)
                index = (index + 1) % len(self.api_keys)
                cache.set('gemini:key_index', index, timeout=None)

                if cache.get(f'gemini:exhausted:{index}') is None:
                    return index, self.api_keys[index]

            remaining = deadline - time.time()
            if remaining <= 0:
                break

            # Django cache has no ttl(); estimate wait as a fixed cooldown window
            wait = min(30, max(remaining, 1))
            logger.info('All Gemini keys cooling down, waiting %ds', int(wait))
            time.sleep(wait)

        raise GeminiClientError('NO_KEYS_AVAILABLE')







    def _cooldown_key(self, index: int, seconds: int) -> None:
        seconds = min(seconds, self.MAX_COOLDOWN_SECONDS)
        cache.set(f'gemini:exhausted:{index}', True, timeout=seconds)
        logger.warning('Gemini key #%d cooldown %ds', index + 1, seconds)

    @staticmethod
    def _error_code(exc: Exception) -> int | None:
        code = getattr(exc, 'code', None)
        return code if isinstance(code, int) else None

    @classmethod
    def _quota_retry_delay(cls, exc: Exception) -> int:
        match = RETRY_DELAY_PATTERN.search(str(exc))
        if match:
            return int(match.group(1))
        return cls.KEY_COOLDOWN_SECONDS

    def _invoke(self, client, model_id: str, prompt: str,
                use_search: bool, require_search: bool = False):
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
            if code == 429 or code in self.TOOL_REJECTED_CODES:
                if require_search:
                    raise
                logger.warning(
                    'Grounding unavailable on %s (%s), degrading to plain call',
                    model_id, code,
                )
                return client.models.generate_content(model=model_id, contents=prompt)
            raise

    def generate(self, prompt: str, use_search: bool = False,
                 require_search: bool = False) -> str:
        last_error: Exception | None = None
        all_rate_limited = True

        for model_id in self.models:
            for _ in range(len(self.api_keys)):
                try:
                    key_index, api_key = self._next_available_key()
                except GeminiClientError:
                    if all_rate_limited and last_error:
                        break
                    raise

                try:
                    client = genai.Client(
                        api_key=api_key,
                        http_options=types.HttpOptions(timeout=60_000),
                    )
                    response = self._invoke(
                        client, model_id, prompt, use_search, require_search,
                    )
                    logger.info(
                        'Gemini call succeeded: model=%s key=#%d search=%s',
                        model_id, key_index + 1, use_search,
                    )
                    return response.text

                except errors.APIError as exc:
                    last_error = exc
                    code = self._error_code(exc)

                    if code in (429, 503):
                        self._cooldown_key(key_index, self._quota_retry_delay(exc))
                        continue

                    all_rate_limited = False

                    if code == 404:
                        logger.warning('Model %s unavailable, falling back', model_id)
                        break

                    if code == 400:
                        logger.error('Gemini key #%d invalid or restricted', key_index + 1)
                        self._cooldown_key(key_index, self.KEY_COOLDOWN_SECONDS)
                        continue

                    logger.error('Gemini API error (%s): %s', code, exc)
                    time.sleep(2)
                    continue

                except Exception as exc:
                    last_error = exc
                    all_rate_limited = False
                    logger.error('Gemini transient error: %s', exc)
                    time.sleep(2)
                    continue

        if all_rate_limited:
            raise GeminiClientError(
                'All Gemini keys quota-exhausted. Check https://ai.dev/rate-limit'
            )
        raise GeminiClientError(f'All Gemini keys and models failed: {last_error}')