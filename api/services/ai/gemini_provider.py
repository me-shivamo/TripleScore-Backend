import os
from typing import AsyncGenerator
import google.generativeai as genai

from .base import AIProvider


class GeminiProvider(AIProvider):
    def __init__(self):
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self._model = genai.GenerativeModel("gemini-1.5-flash")

    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: str,
    ) -> AsyncGenerator[bytes, None]:
        # Convert messages to Gemini format
        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        last_message = messages[-1]["content"]
        full_prompt = f"{system_prompt}\n\n{last_message}" if not history else last_message

        chat = self._model.start_chat(history=history)
        response = await chat.send_message_async(full_prompt, stream=True)

        async for chunk in response:
            if chunk.text:
                yield chunk.text.encode("utf-8")
