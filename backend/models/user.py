from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    login_failures = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    avatar_path = Column(String(500), nullable=True)
    background_path = Column(String(500), nullable=True)
    background_opacity = Column(Float, default=0.3)
    max_rounds = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    carousel_interval = Column(Integer, default=5)
    backgrounds = relationship("UserBackground", back_populates="user", cascade="all, delete-orphan", order_by="UserBackground.position")
    llm_config = relationship("LLMConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
