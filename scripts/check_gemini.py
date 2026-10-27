"""
Smoke-test the Gemini API key and model. 
command I need to run: uv run python scripts/check_gemini.py
"""
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types


def main() -> int:
    load_dotenv()

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY is not set in .env", file=sys.stderr)
        return 1

    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    print(f"model: {model}")

    client = genai.Client(api_key=key)

    try:
        resp = client.models.generate_content(
            model=model,
            contents="Reply with the word OK.",
            config=types.GenerateContentConfig(
                max_output_tokens=1024,
                thinking_config=types.ThinkingConfig(
                    thinking_level="minimal",   # Flash-Lite: stop the default HIGH thinking
                ),
                http_options=types.HttpOptions(timeout=30_000),  # ms
            ),
        )
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"response: {resp.text!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())