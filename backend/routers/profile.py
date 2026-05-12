import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.models.user_background import UserBackground
from backend.schemas.user import ProfileOut, ProfileUpdate, BackgroundOut, BackgroundReorder
from backend.services import file_service
from backend.config import IMAGE_MAX_UPLOAD_SIZE_BYTES, IMAGE_ALLOWED_EXTENSIONS
from backend.utils.response import ok
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("routers.profile")
router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

PILLOW_FORMAT_TO_MIME = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}

EXT_TO_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}

MAX_BACKGROUNDS = 10


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

    # 使用Pillow检测图片格式
    img = Image.open(io.BytesIO(content))
    img_format = img.format
    detected_mime = PILLOW_FORMAT_TO_MIME.get(img_format)
    if not detected_mime:
        raise AppException(
            code=4011,
            message=f"Unsupported image format: {img_format}",
            status_code=400,
        )

    # 检查扩展名和实际内容是否匹配
    expected_mime = EXT_TO_MIME.get(ext)
    if expected_mime and detected_mime != expected_mime:
        raise AppException(
            code=4011,
            message=f"File content does not match expected image type. Detected: {detected_mime}",
            status_code=400,
        )

    # 验证图片完整性
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
    if body.background_opacity is not None:
        current_user.background_opacity = body.background_opacity
    if body.carousel_interval is not None:
        current_user.carousel_interval = body.carousel_interval
    if body.max_rounds is not None:
        current_user.max_rounds = body.max_rounds
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

    old_path = current_user.avatar_path
    relative_path = file_service.save_file(current_user.id, file.filename, content, "profile")
    current_user.avatar_path = relative_path
    db.commit()
    db.refresh(current_user)
    if old_path:
        file_service.delete_file(old_path)
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

    old_path = current_user.background_path
    relative_path = file_service.save_file(current_user.id, file.filename, content, "profile")
    current_user.background_path = relative_path
    db.commit()
    db.refresh(current_user)
    if old_path:
        file_service.delete_file(old_path)
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


@router.get("/backgrounds")
def list_backgrounds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bgs = db.query(UserBackground).filter(
        UserBackground.user_id == current_user.id
    ).order_by(UserBackground.position).all()
    return ok(data=[BackgroundOut.model_validate(bg).model_dump() for bg in bgs])


@router.post("/backgrounds")
def upload_background_multi(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(UserBackground).filter(UserBackground.user_id == current_user.id).count()
    if count >= MAX_BACKGROUNDS:
        raise AppException(code=4000, message=f"Maximum {MAX_BACKGROUNDS} backgrounds allowed", status_code=400)

    content = file.file.read()
    _validate_image(file, content)

    relative_path = file_service.save_file(current_user.id, file.filename, content, "profile")

    bg = UserBackground(
        user_id=current_user.id,
        image_path=relative_path,
        position=count,
    )
    db.add(bg)
    db.commit()
    db.refresh(bg)
    return ok(data=BackgroundOut.model_validate(bg).model_dump())


@router.delete("/backgrounds/{bg_id}")
def delete_background_multi(
    bg_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bg = db.query(UserBackground).filter(
        UserBackground.id == bg_id,
        UserBackground.user_id == current_user.id,
    ).first()
    if not bg:
        raise AppException(code=4004, message="Background not found", status_code=404)

    file_service.delete_file(bg.image_path)
    db.delete(bg)
    db.flush()

    remaining = db.query(UserBackground).filter(
        UserBackground.user_id == current_user.id
    ).order_by(UserBackground.position).all()
    for i, item in enumerate(remaining):
        item.position = i

    db.commit()
    return ok(data=None)


@router.put("/backgrounds/reorder")
def reorder_backgrounds(
    body: BackgroundReorder,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bgs = db.query(UserBackground).filter(
        UserBackground.user_id == current_user.id,
        UserBackground.id.in_(body.background_ids),
    ).all()

    if len(bgs) != len(body.background_ids):
        raise AppException(code=4000, message="One or more invalid background IDs", status_code=400)

    bg_map = {bg.id: bg for bg in bgs}
    for pos, bg_id in enumerate(body.background_ids):
        bg_map[bg_id].position = pos

    db.commit()
    return ok(data=None)
