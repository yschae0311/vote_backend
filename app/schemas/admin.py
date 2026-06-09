from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UploadResponse(BaseModel):
    url: str


class ResetVotesResponse(BaseModel):
    deleted_ballots: int
