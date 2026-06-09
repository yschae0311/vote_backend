from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models import Ballot, Candidate, Poll, VoteItem
from app.schemas.poll import CheckResponse, VoteEntry, VoteSubmit


def _validate_votes(votes: list[VoteEntry], candidate_ids: set[int]) -> None:
    ranks = [v.rank for v in votes]
    cids = [v.candidate_id for v in votes]
    if len(set(ranks)) != len(ranks):
        raise HTTPException(status_code=400, detail="Duplicate ranks")
    if len(set(cids)) != len(cids):
        raise HTTPException(status_code=400, detail="Duplicate candidates")
    for v in votes:
        if v.candidate_id not in candidate_ids:
            raise HTTPException(status_code=400, detail=f"Invalid candidate_id: {v.candidate_id}")


def check_vote(db: Session, poll_id: int, fingerprint: str) -> CheckResponse:
    ballot = (
        db.query(Ballot)
        .options(joinedload(Ballot.items))
        .filter(Ballot.poll_id == poll_id, Ballot.fingerprint == fingerprint)
        .first()
    )
    if not ballot:
        return CheckResponse(voted=False)
    votes = [VoteEntry(rank=item.rank, candidate_id=item.candidate_id) for item in ballot.items]
    votes.sort(key=lambda v: v.rank)
    return CheckResponse(voted=True, votes=votes)


def submit_vote(db: Session, poll: Poll, body: VoteSubmit) -> None:
    if poll.status != "active":
        raise HTTPException(status_code=403, detail="Poll is not active")

    existing = (
        db.query(Ballot)
        .filter(Ballot.poll_id == poll.id, Ballot.fingerprint == body.fingerprint)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already voted")

    candidate_ids = {c.id for c in poll.candidates}
    _validate_votes(body.votes, candidate_ids)

    ballot = Ballot(poll_id=poll.id, fingerprint=body.fingerprint)
    db.add(ballot)
    db.flush()

    for v in body.votes:
        db.add(VoteItem(ballot_id=ballot.id, candidate_id=v.candidate_id, rank=v.rank))

    db.commit()
