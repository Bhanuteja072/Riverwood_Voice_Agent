from groq import Groq
from langdetect import detect
from .config import GROQ_API_KEY
from .prompts import get_first_message, get_system_prompt

_MODEL = "llama-3.3-70b-versatile"
_MAX_TOKENS = 512  # 200 could cut off a 3-4 sentence Hinglish reply mid-word

_client = None


def _get_client() -> Groq:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing. Set it in your environment.")

    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def get_response(
    conversation_history: list,
    user_message: str,
    customer_name: str = "",
) -> tuple[str, list]:
    """
    Append *user_message* to history, call the LLM, append the reply,
    and return (reply_text, updated_history).

    A shallow copy of *conversation_history* is made so the caller's
    original list is never mutated.
    """
    history = list(conversation_history)  # do not mutate caller's list
    history.append({"role": "user", "content": user_message})

    extra_system: dict | None = None
    try:
        if detect(user_message) == "en":
            extra_system = {
                "role": "system",
                "content": (
                    "IMPORTANT: The customer just spoke in pure English. "
                    "You MUST respond in English only. Do not use any Hindi or Hinglish words at all in your reply."
                ),
            }
    except Exception:
        pass

    messages = [{"role": "system", "content": get_system_prompt(customer_name)}] + history
    if extra_system is not None:
        messages.insert(len(messages) - 1, extra_system)

    try:
        response = _get_client().chat.completions.create(
            model=_MODEL,
            messages=messages,
            max_tokens=_MAX_TOKENS,
            temperature=0.8,
        )
    except Exception as exc:
        raise RuntimeError(f"Groq API call failed: {exc}") from exc

    ai_reply: str = response.choices[0].message.content or ""
    history.append({"role": "assistant", "content": ai_reply})

    return ai_reply, history


def get_opening_message(customer_name: str = "") -> tuple[str, list]:
    """
    Return the scripted opening line Riya speaks when the call connects,
    together with a pre-seeded conversation history so follow-up turns
    flow naturally without the LLM re-introducing itself.

    Uses the deterministic get_first_message() — no LLM call needed here.
    """
    opening_text = get_first_message(customer_name)
    seeded_history = [{"role": "assistant", "content": opening_text}]
    return opening_text, seeded_history