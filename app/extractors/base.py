from __future__ import annotations
from typing import Protocol, Type
from pydantic import BaseModel


class LLMExtractor(Protocol):
    name: str

    def extract(
        self, text: str, schema_cls: Type[BaseModel], instructions: str
    ) -> BaseModel: ...