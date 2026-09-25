from .base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    name = 'gemini'

    def generate(self, prompt: str) -> str:
        from research.services.gemini_client import GeminiClient
        return GeminiClient().generate(prompt)