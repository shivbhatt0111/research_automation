from abc import ABC, abstractmethod


class LLMError(Exception):
    pass


class BaseLLMProvider(ABC):
    name: str = 'base'

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Returns raw text response for the given prompt."""