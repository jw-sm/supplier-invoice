from __future__ import annotations
import os
from typing import Type

import anthropic
from pydantic import BaseModel


TOOL_NAME = "record_invoice"


def _clean_schema(node):
    if isinstance(node, dict):
        return {
            k: _clean_schema(v)
            for k, v in node.items()
            if k not in {"title", "default", "examples"}
        }
    if isinstance(node, list):
        return [_clean_schema(v) for v in node]
    return node


class ClaudeExtractor:
    name = "claude"

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")

    def extract(self, text: str, schema_cls: Type[BaseModel], instructions: str) -> BaseModel:
        tool = {
            "name": TOOL_NAME,
            "description": "Record structured invoice data extracted from the document.",
            "input_schema": _clean_schema(schema_cls.model_json_schema()),
        }

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            tools=[tool],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": f"{instructions}\n\n---\n{text}"}],
        )

        block = next(b for b in response.content if b.type == "tool_use")
        return schema_cls.model_validate(block.input)