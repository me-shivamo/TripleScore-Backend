import os
from typing import AsyncGenerator
import anthropic

from .base import AIProvider


class AnthropicProvider(AIProvider):
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: str,
    ) -> AsyncGenerator[bytes, None]:
        async with self._client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text.encode("utf-8")
