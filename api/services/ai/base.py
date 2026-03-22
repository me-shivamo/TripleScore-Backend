from abc import ABC, abstractmethod
from typing import AsyncGenerator


class AIProvider(ABC):
    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],  # [{"role": "user"|"assistant", "content": str}]
        system_prompt: str,
    ) -> AsyncGenerator[bytes, None]:
        """Yield raw UTF-8 bytes of the streaming response."""
        ...
