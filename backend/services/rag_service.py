from __future__ import annotations

from typing import Any, Protocol, override

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError

from backend.config import DATA_DIR
from backend.utils.logger import get_logger

logger = get_logger("services.rag")

_chroma_client: Any = None


class _EmbeddingConfig(Protocol):
    api_key: str
    base_url: str
    model_name: str
    vector_dimension: int


class _RAGConfig(Protocol):
    chunk_size: int
    chunk_overlap: int
    top_k: int
    threshold_dist: float
    query_buffer: int


def _get_chroma_client() -> Any:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = init_chroma_client()
    return _chroma_client


class RemoteAPIEmbeddingFunction(EmbeddingFunction[Documents]):
    """ChromaDB-compatible embedding function backed by an OpenAI-compatible
    remote API (e.g. SiliconFlow, DeepSeek, OpenAI).
    """

    _api_key: str
    _base_url: str
    _model_name: str
    _vector_dimension: int

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        vector_dimension: int,
    ) -> None:
        super().__init__()
        self._api_key = api_key
        self._base_url = base_url
        self._model_name = model_name
        self._vector_dimension = vector_dimension

    @override
    def __call__(self, input: Documents) -> Embeddings:
        client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        try:
            response = client.embeddings.create(
                model=self._model_name,
                input=input,
                dimensions=self._vector_dimension,
            )
            return [list(item.embedding) for item in response.data]  # pyright: ignore[reportReturnType]
        except (APIError, APIConnectionError, APITimeoutError) as exc:
            logger.error("Embedding API call failed: %s", exc)
            raise RuntimeError(f"Embedding API call failed: {exc}") from exc


def init_chroma_client() -> Any:
    chroma_path = str(DATA_DIR / "chroma")
    logger.info("Initializing ChromaDB persistent client at %s", chroma_path)
    client = chromadb.PersistentClient(path=chroma_path)
    logger.info("ChromaDB client initialized successfully")
    return client


def get_or_create_collection(
    user_id: int,
    embedding_config: _EmbeddingConfig,
) -> Any:
    """Get or create a ChromaDB collection for *user_id*.

    Parameters
    ----------
    user_id:
        The owning user's ID — used to derive the collection name.
    embedding_config:
        An object with ``api_key``, ``base_url``, ``model_name``, and
        ``vector_dimension`` attributes (e.g. :class:`EmbeddingConfigOut`).
    """
    collection_name = f"user_{user_id}_docs"

    ef = RemoteAPIEmbeddingFunction(
        api_key=embedding_config.api_key,
        base_url=embedding_config.base_url,
        model_name=embedding_config.model_name,
        vector_dimension=embedding_config.vector_dimension,
    )

    client = _get_chroma_client()
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    logger.info(
        "Collection '%s' ready (count=%d)",
        collection_name,
        collection.count(),
    )
    return collection


import re

def process_document(
    user_id: int,
    file_path: str,
    file_content: str,
    rag_config: _RAGConfig,
    embedding_config: _EmbeddingConfig,
) -> int:
    """Process a document: chunk, embed, and upsert into the user's collection."""
    collection = get_or_create_collection(user_id, embedding_config)

    # Use regex to strip out any image markers (both modern numeric and legacy base64 styles)
    # matching either [image:X] or [image: data:...;base64,...] or generic markdown images 
    # to avoid polluting chunks and embeddings with non-textual data.
    clean_content = re.sub(r'\[image:(?:\d+|\s*data:[^;]+;base64,[A-Za-z0-9+/=\s]+)\]', '', file_content)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=rag_config.chunk_size,
        chunk_overlap=rag_config.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )
    chunks = splitter.split_text(clean_content)

    if not chunks:
        logger.warning("No chunks produced for file '%s' (user %d)", file_path, user_id)
        return 0

    logger.info(
        "Split '%s' into %d chunks (chunk_size=%d, overlap=%d)",
        file_path,
        len(chunks),
        rag_config.chunk_size,
        rag_config.chunk_overlap,
    )

    ids = [f"user_{user_id}_{file_path}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": file_path, "user_id": str(user_id), "chunk_index": str(i)}
        for i in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    logger.info(
        "Upserted %d chunks for '%s' into collection 'user_%d_docs'",
        len(chunks),
        file_path,
        user_id,
    )
    return len(chunks)


def delete_document_chunks(
    user_id: int,
    file_path: str,
    embedding_config: _EmbeddingConfig,
) -> int:
    """Delete all chunks belonging to *file_path* from the user's collection.

    Parameters
    ----------
    user_id:
        The owning user's ID.
    file_path:
        Original file path that was stored as metadata on the chunks.
    embedding_config:
        Embedding provider configuration (needed to access the collection).

    Returns
    -------
    int
        The number of chunks deleted.
    """
    try:
        collection = get_or_create_collection(user_id, embedding_config)

        if collection.count() == 0:
            return 0

        # ChromaDB IDs for this file follow the pattern: user_{user_id}_{file_path}_{index}
        # We need to find and delete all matching chunks.
        results = collection.get(
            where={"source": file_path},
            include=[],
        )
        ids_to_delete = results.get("ids", [])
        if not ids_to_delete:
            logger.debug("No chunks found for file '%s' (user %d)", file_path, user_id)
            return 0

        collection.delete(ids=ids_to_delete)
        logger.info(
            "Deleted %d chunks for file '%s' from collection 'user_%d_docs'",
            len(ids_to_delete),
            file_path,
            user_id,
        )
        return len(ids_to_delete)
    except Exception as exc:
        logger.error(
            "Failed to delete RAG chunks for file '%s' (user %d): %s",
            file_path,
            user_id,
            exc,
        )
        raise


def test_embedding_connection(
    api_key: str,
    base_url: str,
    model_name: str,
    vector_dimension: int,
) -> dict:
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.embeddings.create(
            model=model_name,
            input=["test"],
            dimensions=vector_dimension,
        )
        if response.data and len(response.data) > 0:
            logger.info(
                "Embedding connection test succeeded: model=%s, dim=%d",
                model_name,
                vector_dimension,
            )
            return {"success": True, "message": "Connection successful"}
        return {"success": False, "message": "Embedding API returned empty data"}
    except (APIError, APIConnectionError, APITimeoutError) as exc:
        logger.warning("Embedding connection test failed: %s", exc)
        return {"success": False, "message": str(exc)}
    except Exception as exc:
        logger.error("Unexpected error during embedding connection test: %s", exc)
        return {"success": False, "message": str(exc)}


def query_context(
    user_id: int,
    query_text: str,
    rag_config: _RAGConfig,
    embedding_config: _EmbeddingConfig,
) -> list[str]:
    """Query the user's collection and return relevant document chunks.

    Retrieves ``top_k + query_buffer`` candidates, then filters out any
    whose distance exceeds ``threshold_dist``.

    Parameters
    ----------
    user_id:
        The owning user's ID.
    query_text:
        The search / query string.
    rag_config:
        An object with ``top_k``, ``query_buffer``, and ``threshold_dist``
        attributes.
    embedding_config:
        Embedding provider configuration.

    Returns
    -------
    list[str]
        Up to ``top_k`` document chunks whose distance is within the
        configured threshold, ordered by ascending distance.
    """
    collection = get_or_create_collection(user_id, embedding_config)

    if collection.count() == 0:
        logger.info("Collection for user %d is empty — returning no results", user_id)
        return []

    n_results = min(
        rag_config.top_k + rag_config.query_buffer,
        collection.count(),
    )

    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "distances"],
        )
    except Exception as exc:
        logger.error("ChromaDB query failed for user %d: %s", user_id, exc)
        raise RuntimeError(f"ChromaDB query failed: {exc}") from exc

    docs_raw = results.get("documents") or [[]]
    dists_raw = results.get("distances") or [[]]
    documents: list[str] = docs_raw[0]
    distances: list[float] = dists_raw[0]

    filtered = [
        doc
        for doc, dist in zip(documents, distances)
        if dist <= rag_config.threshold_dist
    ][: rag_config.top_k]

    logger.info(
        "Query returned %d/%d results within threshold %.4f for user %d",
        len(filtered),
        len(documents),
        rag_config.threshold_dist,
        user_id,
    )
    return filtered
