from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


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

    @field_validator("chunk_size")
    @classmethod
    def validate_chunk_size(cls, v: int) -> int:
        if v < 50:
            raise ValueError("chunk_size must be >= 50")
        return v

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v: int) -> int:
        if v < 0:
            raise ValueError("chunk_overlap must be >= 0")
        return v

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        if v < 1:
            raise ValueError("top_k must be >= 1")
        return v

    @field_validator("threshold_dist")
    @classmethod
    def validate_threshold_dist(cls, v: float) -> float:
        if v <= 0 or v > 2.0:
            raise ValueError("threshold_dist must be between 0 and 2.0")
        return v

    @field_validator("query_buffer")
    @classmethod
    def validate_query_buffer(cls, v: int) -> int:
        if v < 0:
            raise ValueError("query_buffer must be >= 0")
        return v


class RAGConfigCreate(RAGConfigBase):
    pass


class RAGConfigOut(RAGConfigBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
