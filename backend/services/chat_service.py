from backend.services.chat_storage import load_messages, save_messages, trim_messages
from backend.services.llm_client import stream_llm_response

DEFAULT_SYSTEM_PROMPT = "你是一个有帮助的助手。"


async def stream_chat_session(
    user_id: int,
    session_id: str,
    content: str,
    config,
    max_rounds: int,
):
    """Orchestrate a chat session: load history, append user msg, stream LLM, save assistant reply."""
    messages = load_messages(user_id, session_id)
    messages.append({"role": "user", "content": content})

    req_messages = trim_messages(messages, max_rounds)
    if not any(m.get("role") == "system" for m in req_messages):
        req_messages.insert(0, {"role": "system", "content": DEFAULT_SYSTEM_PROMPT})

    full_reply = ""
    async for delta in stream_llm_response(
        config.base_url, config.api_key, config.model, req_messages
    ):
        full_reply += delta
        yield delta

    messages.append({"role": "assistant", "content": full_reply})
    messages = trim_messages(messages, max_rounds)
    save_messages(user_id, session_id, messages)
