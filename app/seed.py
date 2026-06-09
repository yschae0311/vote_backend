from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth.jwt import hash_password
from app.config import get_settings
from app.models import Admin, Candidate, Poll

CANDIDATES = [
    ("별빛 여우", "디자인팀 · 김서연", "밤하늘을 안내하는 길잡이", 256),
    ("코드 곰", "플랫폼팀 · 이준호", "든든하게 빌드를 지키는 곰", 28),
    ("클라우드 펭귄", "인프라팀 · 박하늘", "어디든 떠다니는 구름 친구", 200),
    ("새싹 토끼", "그로스팀 · 정유진", "쑥쑥 자라는 성장의 상징", 150),
    ("불꽃 다람쥐", "마케팅팀 · 최민석", "에너지가 넘치는 작은 영웅", 40),
    ("물결 수달", "UX팀 · 한지우", "흐름을 부드럽게 잇는 수달", 220),
    ("번개 치타", "백엔드팀 · 오세훈", "가장 빠른 응답 속도", 70),
    ("달빛 고양이", "브랜드팀 · 윤소라", "조용히 곁을 지키는 동반자", 290),
    ("방패 거북", "보안팀 · 강도현", "느려도 확실한 신뢰의 방패", 170),
    ("무지개 앵무", "디자인팀 · 임채원", "다양함을 품은 컬러풀 친구", 330),
    ("별똥 고래", "데이터팀 · 신우빈", "거대한 데이터의 바다를 항해", 240),
    ("솜사탕 양", "피플팀 · 조은별", "포근한 사내 문화의 상징", 350),
    ("탐험 미어캣", "전략팀 · 배준영", "늘 새로운 기회를 살피는 눈", 55),
    ("숲지기 사슴", "ESG팀 · 문가영", "지속가능함을 지키는 사슴", 140),
    ("파도 돌고래", "세일즈팀 · 권태민", "팀워크로 함께 뛰는 돌고래", 210),
    ("꼬마 로봇 '핀'", "AI팀 · 류하경", "미래를 함께 만드는 동료", 264),
]

def _ensure_admin(db: Session) -> None:
    settings = get_settings()
    if not db.query(Admin).filter(Admin.username == settings.admin_username).first():
        db.add(
            Admin(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
            )
        )


def _seed_mock_polls(db: Session) -> None:
    poll = Poll(
        id=42,
        title="2026 사내 마스코트 공모전",
        subtitle="우리 회사를 대표할 새 마스코트를 함께 골라주세요",
        description="1순위·2순위·3순위를 순서대로 골라 투표합니다. 한 사람당 한 번만 투표할 수 있어요.",
        category="브랜딩",
        status="active",
        closes_at=datetime(2026, 6, 20, 18, 0, tzinfo=timezone.utc),
        eligible_count=312,
    )
    db.add(poll)
    db.flush()

    for i, (name, team, tagline, tint) in enumerate(CANDIDATES, start=1):
        db.add(
            Candidate(
                poll_id=poll.id,
                name=name,
                team=team,
                tagline=tagline,
                tint=tint,
                order_num=i,
            )
        )

    extra_polls = [
        ("2026 상반기 워크샵 장소", "행사", "draft", "이번 워크샵을 어디로 갈지 1~3순위로 골라주세요."),
        ("사내 카페 신메뉴 최종 선정", "복지", "active", "다음 시즌 카페에 들어올 신메뉴를 투표로 정합니다."),
        ("2025 올해의 팀 어워드", "시상", "closed", "한 해 동안 가장 빛난 팀을 뽑는 연말 어워드."),
    ]
    for title, category, status, desc in extra_polls:
        db.add(
            Poll(
                title=title,
                category=category,
                status=status,
                description=desc,
                eligible_count=312,
            )
        )

    db.commit()


def seed_database(db: Session) -> None:
    settings = get_settings()
    _ensure_admin(db)

    if db.query(Poll).count() > 0:
        db.commit()
        return

    if not settings.should_seed_mock_data:
        db.commit()
        return

    _seed_mock_polls(db)
