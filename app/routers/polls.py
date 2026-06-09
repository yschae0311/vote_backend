from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Poll
from app.schemas.poll import CheckResponse, PollOut, VoteSubmit
from app.services.vote_service import check_vote, submit_vote

router = APIRouter(prefix="/polls", tags=["polls"])


def _get_poll_or_404(db: Session, poll_id: int) -> Poll:
    poll = (
        db.query(Poll)
        .options(joinedload(Poll.candidates))
        .filter(Poll.id == poll_id)
        .first()
    )
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll


@router.get("/{poll_id}", response_model=PollOut)
def get_poll(poll_id: int, db: Session = Depends(get_db)) -> Poll:
    poll = _get_poll_or_404(db, poll_id)
    if poll.status != "active":
        raise HTTPException(status_code=403, detail="Poll is not available for voting")
    return poll


@router.get("/{poll_id}/check", response_model=CheckResponse)
def check_poll_vote(
    poll_id: int,
    fingerprint: str = Query(..., min_length=8, max_length=64),
    db: Session = Depends(get_db),
) -> CheckResponse:
    _get_poll_or_404(db, poll_id)
    return check_vote(db, poll_id, fingerprint)


@router.post("/{poll_id}/vote", status_code=201)
def vote_poll(poll_id: int, body: VoteSubmit, db: Session = Depends(get_db)) -> dict:
    poll = _get_poll_or_404(db, poll_id)
    submit_vote(db, poll, body)
    return {"ok": True}
