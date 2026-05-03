import io
from pathlib import Path

import magic
from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.schemas.user import ProfileOut, ProfileUpdate
from backend.services import file_service
from backend.config import IMAGE_MAX_UPLOAD_SIZE_BYTES, IMAGE_ALLOWED_EXTENSIONS
from backend.utils.response import ok
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("routers.profile")
router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

IMAGE_MIME_WHITELIST = {
    "png": ["image/png"],
    "jpg": ["image/jpeg"],
    "jpeg": ["image/jpeg"],
    "webp": ["image/webp"],
    "gif": ["image/gif"],
}


def _validate_image(file: UploadFile, content: bytes) -> str:
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in IMAGE_ALLOWED_EXTENSIONS:
        raise AppException(code=4009, message=f"Image type '.{ext}' is not allowed", status_code=400)

    if len(content) > IMAGE_MAX_UPLOAD_SIZE_BYTES:
        raise AppException(
            code=4010,
            message=f"Image exceeds maximum size of {IMAGE_MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB",
            status_code=400,
        )

    detected_mime = magic.from_buffer(content, mime=True)
    allowed_mimes = IMAGE_MIME_WHITELIST.get(ext, [])
    if detected_mime not in allowed_mimes:
        raise AppException(
            code=4011,
            message=f"File content does not match expected image type. Detected: {detected_mime}",
            status_code=400,
        )

    img = Image.open(io.BytesIO(content))
    img.verify()

    return ext


def _delete_profile_file(user: User, field: str) -> None:
    path_value = getattr(user, field, None)
    if path_value:
        file_service.delete_file(path_value)


@router.get("")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok(data=ProfileOut.model_validate(current_user).model_dump())


@router.put("")
def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.background_opacity = body.background_opacity
    db.commit()
    db.refresh(current_user)
    return ok(data=ProfileOut.model_validate(current_user).model_dump())


@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = file.file.read()
    _validate_image(file, content)

    _delete_profile_file(current_user, "avatar_path")

    relative_path = file_service.save_file(current_user.id, file.filename, content, "profile")
    current_user.avatar_path = relative_path
    db.commit()
    db.refresh(current_user)
    return ok(data=ProfileOut.model_validate(current_user).model_dump())


@router.delete("/avatar")
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _delete_profile_file(current_user, "avatar_path")
    current_user.avatar_path = None
    db.commit()
    db.refresh(current_user)
    return ok(data=ProfileOut.model_validate(current_user).model_dump())


@router.post("/background")
def upload_background(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = file.file.read()
    _validate_image(file, content)

    _delete_profile_file(current_user, "background_path")

    relative_path = file_service.save_file(current_user.id, file.filename, content, "profile")
    current_user.background_path = relative_path
    db.commit()
    db.refresh(current_user)
    return ok(data=ProfileOut.model_validate(current_user).model_dump())


@router.delete("/background")
def delete_background(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _delete_profile_file(current_user, "background_path")
    current_user.background_path = None
    db.commit()
    db.refresh(current_user)
    return ok(data=ProfileOut.model_validate(current_user).model_dump())
