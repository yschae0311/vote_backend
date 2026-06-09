from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import Ballot, Candidate, VoteItem
from app.schemas.poll import ResultRow, ResultsOut


def get_results(db: Session, poll_id: int, eligible_count: int) -> ResultsOut:
    r1 = func.sum(case((VoteItem.rank == 1, 1), else_=0))
    r2 = func.sum(case((VoteItem.rank == 2, 1), else_=0))
    r3 = func.sum(case((VoteItem.rank == 3, 1), else_=0))

    rows_q = (
        db.query(
            Candidate.id,
            Candidate.name,
            Candidate.team,
            Candidate.tagline,
            Candidate.tint,
            func.coalesce(r1, 0).label("r1"),
            func.coalesce(r2, 0).label("r2"),
            func.coalesce(r3, 0).label("r3"),
        )
        .outerjoin(
            VoteItem,
            VoteItem.candidate_id == Candidate.id,
        )
        .outerjoin(
            Ballot,
            (Ballot.id == VoteItem.ballot_id) & (Ballot.poll_id == poll_id),
        )
        .filter(Candidate.poll_id == poll_id)
        .group_by(Candidate.id)
        .order_by((func.coalesce(r1, 0) * 3 + func.coalesce(r2, 0) * 2 + func.coalesce(r3, 0)).desc())
    )

    total_ballots = db.query(func.count(Ballot.id)).filter(Ballot.poll_id == poll_id).scalar() or 0

    rows: list[ResultRow] = []
    for row in rows_q.all():
        r1v, r2v, r3v = int(row.r1), int(row.r2), int(row.r3)
        rows.append(
            ResultRow(
                candidate_id=row.id,
                name=row.name,
                team=row.team,
                tagline=row.tagline,
                tint=row.tint,
                r1=r1v,
                r2=r2v,
                r3=r3v,
                score=r1v * 3 + r2v * 2 + r3v,
            )
        )

    rate = (total_ballots / eligible_count) if eligible_count > 0 else 0.0
    return ResultsOut(
        total_ballots=total_ballots,
        eligible_count=eligible_count,
        participation_rate=round(rate, 4),
        rows=rows,
    )


def results_csv(db: Session, poll_id: int, eligible_count: int) -> str:
    results = get_results(db, poll_id, eligible_count)
    lines = ["rank,candidate_id,name,r1,r2,r3,score"]
    for i, row in enumerate(results.rows, start=1):
        name = row.name.replace('"', '""')
        lines.append(f'{i},{row.candidate_id},"{name}",{row.r1},{row.r2},{row.r3},{row.score}')
    return "\n".join(lines) + "\n"
