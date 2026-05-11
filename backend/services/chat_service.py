from datetime import datetime

from backend.database import SessionLocal
from backend.models.embedding_config import EmbeddingConfig
from backend.models.rag_config import RAGConfig
from backend.models.chat_session import ChatSession
from backend.services.rag_service import query_context
from backend.services.chat_storage import load_messages, save_messages, trim_messages
from backend.services.llm_client import stream_llm_response
from backend.utils.crypto_utils import decrypt_api_key
from backend.utils.logger import get_logger

logger = get_logger("services.chat")

DEFAULT_SYSTEM_PROMPT = "你是一个有帮助的助手。"


def _fetch_rag_context(user_id: int, query: str) -> str | None:
    db = SessionLocal()
    try:
        embedding_config = (
            db.query(EmbeddingConfig)
            .filter(EmbeddingConfig.user_id == user_id)
            .first()
        )
        rag_config = (
            db.query(RAGConfig)
            .filter(RAGConfig.user_id == user_id)
            .first()
        )
        if not embedding_config:
            logger.warning("Embedding config missing for user_id=%d, skipping RAG context", user_id)
            return None
        if not rag_config:
            logger.warning("RAG config missing for user_id=%d, skipping RAG context", user_id)
            return None

        from types import SimpleNamespace
        ec = SimpleNamespace(
            api_key=decrypt_api_key(str(embedding_config.api_key)),
            base_url=str(embedding_config.base_url),
            model_name=str(embedding_config.model_name),
            vector_dimension=int(embedding_config.vector_dimension),
        )

        chunks = query_context(
            user_id, query, rag_config, ec
        )
        if not chunks:
            return None

        return "\n\n".join(chunks)
    except Exception:
        logger.error("RAG context retrieval failed for user %d", user_id, exc_info=True)
        return None
    finally:
        db.close()


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

    # Save user message immediately so it persists even if LLM call fails
    save_messages(user_id, session_id, messages)

    req_messages = trim_messages(messages, max_rounds)
    if not any(m.get("role") == "system" for m in req_messages):
        req_messages.insert(0, {"role": "system", "content": DEFAULT_SYSTEM_PROMPT})

    rag_context = _fetch_rag_context(user_id, content)
    if rag_context:
        for i, msg in enumerate(req_messages):
            if msg.get("role") == "system":
                # Create a copy to prevent modifying the dictionary saved to chat history
                req_messages[i] = msg.copy()
                req_messages[i]["content"] = (
                    f"[系统提示：以下内容是从用户知识库中检索到的相关文档片段，请基于这些检索内容来回答用户的问题。"
                    f"请注意，这些内容来源于用户的文档库，而非用户本人提供的信息。]\n\n"
                    f"<知识库检索结果>\n{rag_context}\n</知识库检索结果>\n\n"
                    f"{msg['content']}"
                )
                break

    api_key = decrypt_api_key(config.api_key)
    full_reply = ""
    try:
        async for delta in stream_llm_response(
            config.base_url, api_key, config.model, req_messages
        ):
            full_reply += delta
            yield delta
    except Exception as e:
        if not full_reply:
            full_reply = f"抱歉，AI 回复时出现错误：{e}"
            yield full_reply
        raise
    finally:
        api_key = ""

    messages.append({"role": "assistant", "content": full_reply})
    messages = trim_messages(messages, max_rounds)
    save_messages(user_id, session_id, messages)

    _update_session_timestamp(user_id, session_id)


def _update_session_timestamp(user_id: int, session_id: str):
    db = SessionLocal()
    try:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.session_id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if session:
            session.updated_at = datetime.utcnow()
            db.commit()
    except Exception:
        logger.warning("Failed to update session timestamp for %s", session_id, exc_info=True)
    finally:
        db.close()
