from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UploadResponse(BaseModel):
    url: str


class PresignRequest(BaseModel):
    filename: str = "image.jpg"
    content_type: str = "image/jpeg"


class PresignResponse(BaseModel):
    upload_url: str
    public_url: str
    key: str


class ResetVotesResponse(BaseModel):
    deleted_ballots: int
