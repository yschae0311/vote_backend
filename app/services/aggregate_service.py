from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models import Ballot, Candidate, Poll, VoteItem
from app.schemas.poll import ResultRow, ResultsOut


def _rank_case(rank: int):
    return func.sum(case((VoteItem.rank == rank, 1), else_=0))


def get_results(db: Session, poll_id: int, eligible_count: int) -> ResultsOut:
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    max_sel = poll.max_selections if poll and poll.max_selections else 3

    r1 = _rank_case(1)
    r2 = _rank_case(2)
    r3 = _rank_case(3)
    r4 = _rank_case(4)
    r5 = _rank_case(5)

    score_expr = (
        func.coalesce(r1, 0) * max_sel
        + func.coalesce(r2, 0) * max(max_sel - 1, 0)
        + func.coalesce(r3, 0) * max(max_sel - 2, 0)
        + func.coalesce(r4, 0) * max(max_sel - 3, 0)
        + func.coalesce(r5, 0) * max(max_sel - 4, 0)
    )

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
            func.coalesce(r4, 0).label("r4"),
            func.coalesce(r5, 0).label("r5"),
        )
        .outerjoin(VoteItem, VoteItem.candidate_id == Candidate.id)
        .outerjoin(Ballot, (Ballot.id == VoteItem.ballot_id) & (Ballot.poll_id == poll_id))
        .filter(Candidate.poll_id == poll_id)
        .group_by(Candidate.id)
        .order_by(score_expr.desc())
    )

    total_ballots = db.query(func.count(Ballot.id)).filter(Ballot.poll_id == poll_id).scalar() or 0

    rows: list[ResultRow] = []
    for row in rows_q.all():
        r1v, r2v, r3v = int(row.r1), int(row.r2), int(row.r3)
        r4v, r5v = int(row.r4), int(row.r5)
        score = sum(
            count * max(max_sel - i, 0)
            for i, count in enumerate([r1v, r2v, r3v, r4v, r5v])
        )
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
                r4=r4v,
                r5=r5v,
                score=score,
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
    lines = ["rank,candidate_id,name,r1,r2,r3,r4,r5,score"]
    for i, row in enumerate(results.rows, start=1):
        name = row.name.replace('"', '""')
        lines.append(
            f'{i},{row.candidate_id},"{name}",{row.r1},{row.r2},{row.r3},{row.r4},{row.r5},{row.score}'
        )
    return "\n".join(lines) + "\n"
