from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class BackgroundOut(BaseModel):
    id: int
    image_path: str
    position: int

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    avatar_path: str | None = None
    background_path: str | None = None
    background_opacity: float = 0.3
    carousel_interval: int = 5
    backgrounds: list[BackgroundOut] = []

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    background_opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    carousel_interval: int | None = Field(default=None, ge=1, le=300)


class BackgroundReorder(BaseModel):
    background_ids: list[int]
