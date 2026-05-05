from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, CheckConstraint

from backend.database import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('pdf','docx','md','png','jpg','jpeg')",
            name="chk_file_type",
        ),
        CheckConstraint(
            "status IN ('queued','processing','ready','error')",
            name="chk_document_status",
        ),
        CheckConstraint(
            "category IN ('sujian','shicui','manbi') OR category IS NULL",
            name="chk_document_category",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    content_text = Column(Text, nullable=True)
    status = Column(String(20), default="queued", index=True)
    error_message = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False, index=True)
    category = Column(String(20), nullable=True, index=True)
    view_count = Column(Integer, default=0)
    last_viewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
