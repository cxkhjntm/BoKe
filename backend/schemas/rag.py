from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmbeddingConfigBase(BaseModel):
    api_key: str
    base_url: str = "https://api.siliconflow.cn/v1"
    model_name: str = "BAAI/bge-large-zh-v1.5"
    vector_dimension: int = 1024


class EmbeddingConfigCreate(EmbeddingConfigBase):
    pass


class EmbeddingConfigOut(EmbeddingConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RAGConfigBase(BaseModel):
    chunk_size: int = 300
    chunk_overlap: int = 50
    top_k: int = 3
    threshold_dist: float = 0.35
    query_buffer: int = 10


class RAGConfigCreate(RAGConfigBase):
    pass


class RAGConfigOut(RAGConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
