import logging

from django.conf import settings

from .base import LLMError
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider

logger = logging.getLogger(__name__)

PROVIDER_REGISTRY = {
    'gemini': GeminiProvider,
    'groq': GroqProvider,
}


class LLMRouter:
    """Routes generation calls through a fallback chain of providers."""

    def __init__(self, use_case: str = 'extraction'):
        if use_case == 'discovery':
            self.chain = settings.LLM_DISCOVERY_ORDER
        else:
            self.chain = settings.LLM_EXTRACTION_ORDER

    @staticmethod
    def _available(name: str) -> bool:
        availability = {
            'groq': any(k for k in settings.GROQ_API_KEYS if k),
            'gemini': any(k for k in settings.GEMINI_API_KEYS if k),
        }
        return availability.get(name, False)

    def generate(self, prompt: str) -> str:
        errors = []

        for name in self.chain:
            if not self._available(name):
                continue

            provider = PROVIDER_REGISTRY[name]()
            try:
                result = provider.generate(prompt)
                logger.info('LLM call via %s succeeded', name)
                return result
            except Exception as exc:
                logger.warning('LLM provider %s failed: %s', name, exc)
                errors.append(f'{name}: {exc}')

        raise LLMError(f'All LLM providers failed: {errors}')