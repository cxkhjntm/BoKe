from pydantic import BaseModel, Field, field_validator


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
    max_rounds: int = 10
    backgrounds: list[BackgroundOut] = []

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    background_opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    carousel_interval: int | None = Field(default=None, ge=1, le=300)
    max_rounds: int | None = Field(default=None, ge=0, le=30)


class BackgroundReorder(BaseModel):
    background_ids: list[int] = Field(min_length=1)

    @field_validator("background_ids")
    @classmethod
    def validate_unique_ids(cls, v: list[int]) -> list[int]:
        if len(v) != len(set(v)):
            raise ValueError("background_ids must not contain duplicates")
        return v
