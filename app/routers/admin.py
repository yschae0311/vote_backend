import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.deps import get_current_admin
from app.auth.jwt import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.database import get_db
from app.models import Admin, Ballot, Candidate, Poll
from app.schemas.admin import LoginRequest, ResetVotesResponse, TokenResponse, UploadResponse
from app.schemas.poll import (
    CandidateCreate,
    CandidateOut,
    CandidateUpdate,
    PollCreate,
    PollListItem,
    PollOut,
    PollUpdate,
    ResultsOut,
)
from app.services.aggregate_service import get_results, results_csv

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    admin = db.query(Admin).filter(Admin.username == body.username).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(admin.username))


@router.get("/polls", response_model=list[PollListItem])
def list_polls(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> list[PollListItem]:
    polls = db.query(Poll).order_by(Poll.created_at.desc()).all()
    items: list[PollListItem] = []
    for p in polls:
        cand_count = db.query(func.count(Candidate.id)).filter(Candidate.poll_id == p.id).scalar() or 0
        ballot_count = db.query(func.count(Ballot.id)).filter(Ballot.poll_id == p.id).scalar() or 0
        items.append(
            PollListItem(
                id=p.id,
                title=p.title,
                category=p.category,
                status=p.status,
                candidates=cand_count,
                ballots=ballot_count,
                eligible=p.eligible_count,
                created_at=p.created_at,
                closes_at=p.closes_at,
                desc=p.description,
            )
        )
    return items


@router.post("/polls", response_model=PollOut, status_code=201)
def create_poll(
    body: PollCreate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> Poll:
    poll = Poll(
        title=body.title,
        subtitle=body.subtitle,
        description=body.description,
        category=body.category,
        status="draft",
        closes_at=body.closes_at,
        eligible_count=body.eligible_count,
    )
    db.add(poll)
    db.flush()
    for i, c in enumerate(body.candidates):
        db.add(
            Candidate(
                poll_id=poll.id,
                name=c.name,
                team=c.team,
                tagline=c.tagline,
                image_url=c.image_url,
                tint=c.tint,
                order_num=i,
            )
        )
    db.commit()
    db.refresh(poll)
    return db.query(Poll).options(joinedload(Poll.candidates)).filter(Poll.id == poll.id).one()


@router.get("/polls/{poll_id}", response_model=PollOut)
def get_poll_admin(
    poll_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> Poll:
    poll = db.query(Poll).options(joinedload(Poll.candidates)).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll


@router.patch("/polls/{poll_id}", response_model=PollOut)
def update_poll(
    poll_id: int,
    body: PollUpdate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> Poll:
    poll = db.query(Poll).options(joinedload(Poll.candidates)).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(poll, field, value)
    db.commit()
    db.refresh(poll)
    return poll


@router.delete("/polls/{poll_id}", status_code=204)
def delete_poll(
    poll_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> None:
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    db.delete(poll)
    db.commit()


@router.post("/polls/{poll_id}/candidates", response_model=CandidateOut, status_code=201)
def add_candidate(
    poll_id: int,
    body: CandidateCreate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> Candidate:
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    max_order = db.query(func.max(Candidate.order_num)).filter(Candidate.poll_id == poll_id).scalar() or 0
    cand = Candidate(
        poll_id=poll_id,
        name=body.name,
        team=body.team,
        tagline=body.tagline,
        image_url=body.image_url,
        tint=body.tint,
        order_num=max_order + 1,
    )
    db.add(cand)
    db.commit()
    db.refresh(cand)
    return cand


@router.patch("/polls/{poll_id}/candidates/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    poll_id: int,
    candidate_id: int,
    body: CandidateUpdate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> Candidate:
    cand = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.poll_id == poll_id)
        .first()
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cand, field, value)
    db.commit()
    db.refresh(cand)
    return cand


@router.delete("/polls/{poll_id}/candidates/{candidate_id}", status_code=204)
def delete_candidate(
    poll_id: int,
    candidate_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> None:
    cand = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id, Candidate.poll_id == poll_id)
        .first()
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(cand)
    db.commit()


@router.post("/polls/{poll_id}/reset", response_model=ResetVotesResponse)
def reset_poll_votes(
    poll_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> ResetVotesResponse:
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    ballots = db.query(Ballot).filter(Ballot.poll_id == poll_id).all()
    count = len(ballots)
    for ballot in ballots:
        db.delete(ballot)
    db.commit()
    return ResetVotesResponse(deleted_ballots=count)


@router.get("/polls/{poll_id}/results", response_model=ResultsOut)
def poll_results(
    poll_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> ResultsOut:
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return get_results(db, poll_id, poll.eligible_count)


@router.get("/polls/{poll_id}/results/csv")
def poll_results_csv(
    poll_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
) -> PlainTextResponse:
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    content = results_csv(db, poll_id, poll.eligible_count)
    return PlainTextResponse(content, media_type="text/csv")


@router.post("/upload/image", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    _admin: Admin = Depends(get_current_admin),
) -> UploadResponse:
    media = settings.media_path
    media.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "img.jpg").suffix or ".jpg"
    name = f"{uuid.uuid4().hex}{ext}"
    dest = media / name
    content = await file.read()
    dest.write_bytes(content)
    return UploadResponse(url=f"/media/{name}")
