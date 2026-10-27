from __future__ import annotations
import os
from typing import Type

from google import genai
from google.genai import types
from pydantic import BaseModel


class GeminiExtractor:
    name = "gemini"

    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    def extract(self, text: str, schema_cls: Type[BaseModel], instructions: str) -> BaseModel:
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"{instructions}\n\n---\n{text}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema_cls,
                temperature=0,
                max_output_tokens=16_384,
                thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                http_options=types.HttpOptions(timeout=90_000),
            ),
        )
        return schema_cls.model_validate_json(response.text)