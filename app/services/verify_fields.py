from fastapi import HTTPException

ALLOWED = frozenset({"name", "email", "phone"})
DEFAULT_FIELDS = ("name", "email", "phone")


def parse_verify_fields(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return list(DEFAULT_FIELDS)
    fields = [f.strip() for f in raw.split(",") if f.strip() in ALLOWED]
    return fields or list(DEFAULT_FIELDS)


def serialize_verify_fields(fields: list[str]) -> str:
    cleaned = [f for f in fields if f in ALLOWED]
    if not cleaned:
        raise HTTPException(status_code=400, detail="인증 항목을 1개 이상 선택해주세요.")
    return ",".join(dict.fromkeys(cleaned))


def validate_verify_fields_list(fields: list[str]) -> list[str]:
    cleaned = [f for f in fields if f in ALLOWED]
    if not cleaned:
        raise HTTPException(status_code=400, detail="인증 항목을 1개 이상 선택해주세요.")
    return list(dict.fromkeys(cleaned))
