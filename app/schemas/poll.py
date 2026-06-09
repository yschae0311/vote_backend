from datetime import datetime

from pydantic import BaseModel, Field


class CandidateOut(BaseModel):
    id: int
    name: str
    team: str | None = None
    tagline: str | None = None
    image_url: str | None = None
    tint: int = 256

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
    candidates: list[CandidateOut]

    model_config = {"from_attributes": True}


class VoteEntry(BaseModel):
    rank: int = Field(ge=1, le=3)
    candidate_id: int


class VoteSubmit(BaseModel):
    fingerprint: str = Field(min_length=8, max_length=64)
    votes: list[VoteEntry] = Field(min_length=1, max_length=3)


class CheckResponse(BaseModel):
    voted: bool
    votes: list[VoteEntry] | None = None


class PollListItem(BaseModel):
    id: int
    title: str
    category: str
    status: str
    candidates: int
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
    tint: int = 256


class PollCreate(BaseModel):
    title: str
    subtitle: str | None = None
    description: str | None = None
    category: str = "기타"
    closes_at: datetime | None = None
    eligible_count: int = 312
    candidates: list[CandidateCreate] = Field(min_length=2)


class PollUpdate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    description: str | None = None
    category: str | None = None
    status: str | None = None
    closes_at: datetime | None = None
    eligible_count: int | None = None


class CandidateUpdate(BaseModel):
    name: str | None = None
    team: str | None = None
    tagline: str | None = None
    image_url: str | None = None
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
    score: int


class ResultsOut(BaseModel):
    total_ballots: int
    eligible_count: int
    participation_rate: float
    rows: list[ResultRow]
