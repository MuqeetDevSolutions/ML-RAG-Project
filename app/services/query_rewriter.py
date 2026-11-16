"""
Query Rewriter — follow-up questions ko standalone banata hai.

Problem:
    User: "Who is Carl?"
    User: "What about Susan?"
    
    "What about Susan?" ek standalone question nahi hai. Kiske bare me?
    
Solution:
    LLM se poochte hain: "Is follow-up ko standalone question banao,
    history ke context me."
    
    Result: "Who is Susan?"

Design:
    - Sirf tab chalta hai jab history mojood ho (pehla sawaal skip)
    - Config flag se on/off
    - Fallback: agar rewrite fail ho jaye, naive combine use karo
    - Ek chota fast LLM prompt (low tokens, fast response)
"""

from typing import List, Dict, Optional

from app.core.config import settings
from app.services.llm import generate


REWRITE_SYSTEM = """You are a query rewriting assistant.

Your job: convert a user's follow-up question into a STANDALONE question,
using the conversation history to resolve pronouns and context.

RULES:
1. Read the conversation history to understand what the follow-up refers to.
2. Output ONLY the rewritten standalone question. No explanations, no quotes.
3. Keep it short (max 30 words).
4. If the question is already standalone, output it unchanged.
5. Do NOT answer the question — just rewrite it.
6. Preserve the user's language (if question is in Urdu, rewrite in Urdu).
7. Do NOT add facts or details that are not in the history.

EXAMPLES:

History:
  User: Who is Carl?
  Assistant: Carl is a watchmaker...
Follow-up: What about Susan?
Output: Who is Susan?

History:
  User: Tell me about the watch.
  Assistant: The watch allows time travel...
Follow-up: How does it work?
Output: How does the watch work?

History:
  User: Who is the Emperor?
  Assistant: Emperor Valior rules the Earthlings...
Follow-up: And his ministers?
Output: Who are Emperor Valior's ministers?

History:
  User: What is RAG?
  Assistant: RAG is...
Follow-up: What is the capital of France?
Output: What is the capital of France?
"""


def should_rewrite(
    question: str,
    history: Optional[List[Dict[str, str]]],
) -> bool:
    """
    Kya is question ko rewrite karna chahiye?

    - Config off? → nahi
    - History khaali? → nahi (pehla sawaal)
    - Question bohot chota/pronoun-based? → haan (jaisa "what about X")
    - Warna bhi haan (LLM decide karega)
    """
    if not settings.QUERY_REWRITE_ENABLED:
        return False
    if not history:
        return False
    # Kam se kam 2 turns (1 user + 1 assistant) chahiye
    if len(history) < 2:
        return False
    return True


def rewrite_query(
    question: str,
    history: Optional[List[Dict[str, str]]],
) -> str:
    """
    Follow-up question ko standalone banao.

    Args:
        question: user ka current sawaal.
        history: previous turns (list of {role, content}).

    Returns:
        Standalone question (ya original agar rewrite skip/fail).
    """
    if not should_rewrite(question, history):
        return question

    # Last N turns le lo (bahut purane context ki zaroorat nahi)
    max_h = settings.QUERY_REWRITE_MAX_HISTORY
    recent = history[-max_h:] if len(history) > max_h else history

    # History ko readable format me
    history_text_parts = []
    for turn in recent:
        role = turn.get("role", "user")
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        # Chhota truncate (bahut lambe answers ki zaroorat nahi)
        if role == "assistant" and len(content) > 300:
            content = content[:300].rstrip() + "..."
        history_text_parts.append(f"{role.upper()}: {content}")

    if not history_text_parts:
        return question

    history_text = "\n".join(history_text_parts)

    user_prompt = (
        "CONVERSATION HISTORY:\n"
        "--------------------\n"
        f"{history_text}\n"
        "--------------------\n\n"
        f"FOLLOW-UP QUESTION: {question}\n\n"
        "Rewrite the FOLLOW-UP QUESTION as a standalone question "
        "(output ONLY the rewritten question, nothing else):"
    )

    try:
        rewritten = generate(
            prompt=user_prompt,
            system=REWRITE_SYSTEM,
            temperature=0.0,
            max_tokens=80,
        )
    except Exception as e:
        # Rewrite fail ho jaye to original return karo
        print(f"[query_rewriter] Failed: {type(e).__name__}: {e}. Using original.")
        return question

    rewritten = (rewritten or "").strip()

    # Sanity: khaali ya bohot lamba? Ignore karo
    if not rewritten or len(rewritten) > 300:
        return question

    # Sanity: LLM ne answer type kar diya? (bahut lamba to nahi — bas 30 words)
    if len(rewritten.split()) > 40:
        return question

    # Quotes hata do agar LLM ne quotes me wrap kiya ho
    if rewritten.startswith(('"', "'")) and rewritten.endswith(('"', "'")):
        rewritten = rewritten[1:-1].strip()

    return rewritten


def rewrite_or_fallback(
    question: str,
    history: Optional[List[Dict[str, str]]],
) -> tuple[str, bool]:
    """
    Convenience wrapper — rewrite + flag return.

    Returns:
        (standalone_question, was_rewritten)
    """
    rewritten = rewrite_query(question, history)
    was_rewritten = rewritten != question
    return rewritten, was_rewritten