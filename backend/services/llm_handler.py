from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv

load_dotenv()


class LLMHandler:
    def __init__(self) -> None:
        self.provider: Literal["gemini", "claude"] = os.getenv("LLM_PROVIDER", "gemini").lower()  # type: ignore[assignment]
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.claude_model = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")

    def generate(self, user_query: str, context: str) -> str:
        if not context.strip():
            return "I could not find enough information in the knowledge base to answer confidently."

        if self.provider == "claude":
            return self._call_claude(user_query, context)
        return self._call_gemini(user_query, context)

    @staticmethod
    def _build_prompt(user_query: str, context: str) -> str:
        return f"""
You are a healthcare customer support assistant.
Use only the retrieved context to answer. Do not invent facts.
If the context does not contain the answer, reply:
"I could not find enough information in the knowledge base to answer confidently."
Never provide diagnosis. Keep guidance non-diagnostic and safe.

Retrieved context:
{context}

User question:
{user_query}
""".strip()

    def _call_gemini(self, user_query: str, context: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return self._fallback_response(context)

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.gemini_model)
            prompt = self._build_prompt(user_query, context)
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            return text if text else self._fallback_response(context)
        except Exception:
            return self._fallback_response(context)

    def _call_claude(self, user_query: str, context: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self._fallback_response(context)

        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            prompt = self._build_prompt(user_query, context)
            message = client.messages.create(
                model=self.claude_model,
                max_tokens=350,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            blocks = message.content
            if not blocks:
                return self._fallback_response(context)
            answer = "".join(getattr(block, "text", "") for block in blocks).strip()
            return answer if answer else self._fallback_response(context)
        except Exception:
            return self._fallback_response(context)

    @staticmethod
    def _fallback_response(context: str) -> str:
        snippet = context.split("\n")[0] if context else ""
        if not snippet:
            return "I could not find enough information in the knowledge base to answer confidently."
        return f"Based on available records: {snippet}"
