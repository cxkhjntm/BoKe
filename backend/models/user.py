from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
