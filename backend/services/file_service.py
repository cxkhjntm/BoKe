import uuid
from pathlib import Path

from backend.config import STORAGE_PATH
from backend.utils.logger import get_logger

logger = get_logger("services.file")


def get_user_storage(user_id: int) -> Path:
    """Get or create user storage directory."""
    user_dir = STORAGE_PATH / str(user_id)
    for sub in ("original", "processed", "thumbnails"):
        (user_dir / sub).mkdir(parents=True, exist_ok=True)
    return user_dir


def save_file(user_id: int, filename: str, file_content: bytes, subfolder: str = "original") -> str:
    """Save file with UUID name. Returns relative path from STORAGE_PATH."""
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    user_dir = get_user_storage(user_id)
    target_dir = user_dir / subfolder
    target_path = target_dir / unique_name

    # Path traversal check
    resolved = target_path.resolve()
    if not resolved.is_relative_to(STORAGE_PATH.resolve()):
        raise ValueError("Path traversal detected")

    target_path.write_bytes(file_content)
    relative_path = str(target_path.relative_to(STORAGE_PATH))
    logger.info("File saved: %s (%d bytes)", relative_path, len(file_content))
    return relative_path


def delete_file(relative_path: str) -> None:
    """Delete a file relative to STORAGE_PATH."""
    full_path = STORAGE_PATH / relative_path
    if full_path.exists():
        full_path.unlink()
        logger.info("File deleted: %s", relative_path)


def get_file_path(relative_path: str) -> Path:
    """Get absolute path from relative path. Validates no traversal."""
    full_path = (STORAGE_PATH / relative_path).resolve()
    if not full_path.is_relative_to(STORAGE_PATH.resolve()):
        raise ValueError("Path traversal detected")
    return full_path
