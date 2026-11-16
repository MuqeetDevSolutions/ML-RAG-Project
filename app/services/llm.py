"""
LLM service (Groq — OpenAI-compatible).

Groq OpenAI ke client library se compatible hai.

Ab `generate()` aur `generate_with_usage()` ek optional `history`
parameter leti hain — list of {"role", "content"} dicts. Yeh
multi-turn conversations ke liye zaroori hai.
"""

from typing import Optional, List, Dict

from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
)

from app.core.config import settings


DEFAULT_MODEL = settings.LLM_MODEL


_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        key = settings.GROQ_API_KEY
        if not key or key.startswith("gsk-your"):
            raise RuntimeError(
                "GROQ_API_KEY set nahi hai. '.env' file banao "
                "project root me aur usme apni real key daalo. "
                "Format: GROQ_API_KEY=gsk_..."
            )
        _client = OpenAI(
            api_key=key,
            base_url=settings.GROQ_BASE_URL,
        )
    return _client


def _build_messages(
    prompt: str,
    system: Optional[str],
    history: Optional[List[Dict[str, str]]],
) -> List[Dict[str, str]]:
    """Messages list banao: system + history + current user prompt."""
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    if history:
        for turn in history:
            role = turn.get("role")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})
    return messages


def generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Ek prompt bhejo aur plain text answer wapas lo.

    history: optional list of {"role": "user"|"assistant", "content": "..."}.
    """
    temperature = (
        settings.LLM_TEMPERATURE if temperature is None else temperature
    )
    max_tokens = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    messages = _build_messages(prompt, system, history)

    try:
        resp = get_client().chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except AuthenticationError as e:
        raise RuntimeError(
            f"Groq authentication failed — API key ghalat ya expired hai. ({e})"
        )
    except RateLimitError as e:
        raise RuntimeError(
            f"Groq rate limit — thori der baad try karo. "
            f"(Free tier: 30 req/min) ({e})"
        )
    except APIConnectionError as e:
        raise RuntimeError(
            f"Groq se connect nahi ho saka — internet check karo. ({e})"
        )
    except APIError as e:
        raise RuntimeError(f"Groq API error: {e}")

    if not resp.choices:
        raise RuntimeError("Groq ne koi response nahi diya.")

    return (resp.choices[0].message.content or "").strip()


def generate_with_usage(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict:
    """
    Same as generate(), lekin usage info ke sath.
    """
    temperature = (
        settings.LLM_TEMPERATURE if temperature is None else temperature
    )
    max_tokens = settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    messages = _build_messages(prompt, system, history)

    resp = get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    usage = {
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "total_tokens": resp.usage.total_tokens if resp.usage else 0,
    }
    text = (resp.choices[0].message.content or "").strip() if resp.choices else ""

    return {"text": text, "usage": usage, "model": model}