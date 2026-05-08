from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class EmbeddingConfig(Base):
    __tablename__ = "embedding_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    api_key = Column(String(500), nullable=True)
    base_url = Column(String(500), nullable=True)
    model_name = Column(String(100), nullable=True)
    vector_dimension = Column(Integer, default=1024)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="embedding_config")
