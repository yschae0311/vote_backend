from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.services.verify_fields import parse_verify_fields, validate_verify_fields_list

PollType = Literal["open", "restricted"]
VerifyField = Literal["name", "email", "phone"]


class CandidateOut(BaseModel):
    id: int
    name: str
    team: str | None = None
    tagline: str | None = None
    image_url: str | None = None
    figma_url: str | None = None
    tint: int = 256

    model_config = {"from_attributes": True}


class PollPublicOut(BaseModel):
    id: int
    title: str
    subtitle: str | None = None
    description: str | None = None
    category: str
    status: str
    closes_at: datetime | None = None
    max_selections: int = 3
    candidates: list[CandidateOut]

    model_config = {"from_attributes": True}


class PollOut(BaseModel):
    id: int
    title: str
    subtitle: str | None = None
    description: str | None = None
    category: str
    status: str
    closes_at: datetime | None = None
    eligible_count: int
    max_selections: int = 3
    poll_type: PollType = "open"
    verify_fields: list[VerifyField] = Field(default_factory=lambda: ["name", "email", "phone"])
    candidates: list[CandidateOut]

    model_config = {"from_attributes": True}

    @field_validator("verify_fields", mode="before")
    @classmethod
    def _parse_verify_fields(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return parse_verify_fields(v)  # type: ignore[return-value]
        return v  # type: ignore[return-value]


class VoteEntry(BaseModel):
    rank: int = Field(ge=1, le=5)
    candidate_id: int


class VoteSubmit(BaseModel):
    fingerprint: str = Field(min_length=8, max_length=64)
    voter_token: str | None = None
    votes: list[VoteEntry] = Field(min_length=1, max_length=5)


class VerifyVoterRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)


class VerifyVoterResponse(BaseModel):
    voter_token: str
    voter_name: str
    already_voted: bool = False


class CheckResponse(BaseModel):
    voted: bool
    votes: list[VoteEntry] | None = None


class PollListItem(BaseModel):
    id: int
    title: str
    category: str
    status: str
    candidates: int
    max_selections: int = 3
    poll_type: PollType = "open"
    ballots: int
    eligible: int
    created_at: datetime
    closes_at: datetime | None = None
    desc: str | None = None


class CandidateCreate(BaseModel):
    name: str
    team: str | None = None
    tagline: str | None = None
    image_url: str | None = None
    figma_url: str | None = None
    tint: int = 256


class PollCreate(BaseModel):
    title: str
    subtitle: str | None = None
    description: str | None = None
    category: str = "기타"
    closes_at: datetime | None = None
    eligible_count: int = 312
    max_selections: int = Field(default=3, ge=1, le=5)
    poll_type: PollType = "open"
    verify_fields: list[VerifyField] = Field(default_factory=lambda: ["email"])
    candidates: list[CandidateCreate] = Field(min_length=2)

    @field_validator("verify_fields")
    @classmethod
    def _validate_verify_fields(cls, v: list[str]) -> list[str]:
        return validate_verify_fields_list(v)  # type: ignore[return-value]


class PollUpdate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    description: str | None = None
    category: str | None = None
    status: str | None = None
    closes_at: datetime | None = None
    eligible_count: int | None = None
    max_selections: int | None = Field(default=None, ge=1, le=5)
    poll_type: PollType | None = None
    verify_fields: list[VerifyField] | None = None

    @field_validator("verify_fields")
    @classmethod
    def _validate_verify_fields(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return validate_verify_fields_list(v)  # type: ignore[return-value]


class EligibleVoterOut(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    voted: bool = False
    voted_at: datetime | None = None

    model_config = {"from_attributes": True}


class RevokeVoterVoteResponse(BaseModel):
    revoked: bool = True


class EligibleVoterCreate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)


class EligibleVoterBulkCreate(BaseModel):
    voters: list[EligibleVoterCreate] = Field(min_length=1)


class CandidateUpdate(BaseModel):
    name: str | None = None
    team: str | None = None
    tagline: str | None = None
    image_url: str | None = None
    figma_url: str | None = None
    tint: int | None = None


class ResultRow(BaseModel):
    candidate_id: int
    name: str
    team: str | None = None
    tagline: str | None = None
    tint: int
    r1: int
    r2: int
    r3: int
    r4: int = 0
    r5: int = 0
    score: int


class ResultsOut(BaseModel):
    total_ballots: int
    eligible_count: int
    participation_rate: float
    rows: list[ResultRow]
