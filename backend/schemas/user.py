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


class ProfileOut(BaseModel):
    avatar_path: str | None = None
    background_path: str | None = None
    background_opacity: float = 0.3
    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    background_opacity: float = Field(ge=0.0, le=1.0)
