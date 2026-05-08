from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.models.embedding_config import EmbeddingConfig
from backend.models.rag_config import RAGConfig
from backend.schemas.rag import (
    EmbeddingConfigCreate,
    RAGConfigCreate,
    RAGConfigOut,
)
from backend.services import rag_service
from backend.utils.response import ok
from backend.utils.crypto_utils import encrypt_api_key

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Config"])


def _mask_api_key(key: str | None) -> str | None:
    if not key:
        return key
    if len(key) < 12:
        return "***"
    return key[:8] + "***" + key[-4:]


def _embedding_to_out(config: EmbeddingConfig) -> dict:
    return {
        "id": config.id,
        "user_id": config.user_id,
        "api_key": _mask_api_key(config.api_key),
        "base_url": config.base_url,
        "model_name": config.model_name,
        "vector_dimension": config.vector_dimension,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


@router.get("/embedding-config")
def get_embedding_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(EmbeddingConfig).filter(EmbeddingConfig.user_id == user.id).first()
    if not config:
        return ok(data=None)
    return ok(data=_embedding_to_out(config))


@router.post("/embedding-config")
def upsert_embedding_config(
    body: EmbeddingConfigCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(EmbeddingConfig).filter(EmbeddingConfig.user_id == user.id).first()
    encrypted_key = encrypt_api_key(body.api_key)
    if config:
        config.api_key = encrypted_key
        config.base_url = body.base_url
        config.model_name = body.model_name
        config.vector_dimension = body.vector_dimension
    else:
        config = EmbeddingConfig(
            user_id=user.id,
            api_key=encrypted_key,
            base_url=body.base_url,
            model_name=body.model_name,
            vector_dimension=body.vector_dimension,
        )
        db.add(config)
    db.commit()
    db.refresh(config)
    return ok(data=_embedding_to_out(config))


@router.post("/test-connection")
def test_embedding_connection(
    body: EmbeddingConfigCreate,
    user: User = Depends(get_current_user),
):
    result = rag_service.test_embedding_connection(
        api_key=body.api_key,
        base_url=body.base_url,
        model_name=body.model_name,
        vector_dimension=body.vector_dimension,
    )
    return ok(data=result)


@router.get("/config")
def get_rag_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(RAGConfig).filter(RAGConfig.user_id == user.id).first()
    if not config:
        return ok(data=None)
    return ok(data=RAGConfigOut.model_validate(config).model_dump())


@router.post("/config")
def upsert_rag_config(
    body: RAGConfigCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(RAGConfig).filter(RAGConfig.user_id == user.id).first()
    if config:
        config.chunk_size = body.chunk_size
        config.chunk_overlap = body.chunk_overlap
        config.top_k = body.top_k
        config.threshold_dist = body.threshold_dist
        config.query_buffer = body.query_buffer
    else:
        config = RAGConfig(
            user_id=user.id,
            chunk_size=body.chunk_size,
            chunk_overlap=body.chunk_overlap,
            top_k=body.top_k,
            threshold_dist=body.threshold_dist,
            query_buffer=body.query_buffer,
        )
        db.add(config)
    db.commit()
    db.refresh(config)
    return ok(data=RAGConfigOut.model_validate(config).model_dump())
