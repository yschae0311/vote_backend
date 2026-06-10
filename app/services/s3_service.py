import logging
import uuid
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.config import Config

from app.config import Settings

logger = logging.getLogger(__name__)


def public_media_url(settings: Settings, key: str) -> str:
    """CloudFront 공개 URL. CLOUDFRONT_URL 에 /vote 가 붙어 있어도 key 와 중복되지 않게 정규화."""
    base = settings.cloudfront_url.strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = f"https://{base}"

    prefix = settings.s3_key_prefix.strip("/")
    if prefix:
        suffix = f"/{prefix}"
        if base.endswith(suffix):
            base = base[: -len(suffix)]

    return f"{base}/{key}"


def create_presigned_upload(settings: Settings, filename: str, content_type: str) -> dict[str, str]:
    ext = Path(filename).suffix.lower() or ".jpg"
    prefix = settings.s3_key_prefix.rstrip("/")
    key = f"{prefix}/{uuid.uuid4().hex}{ext}"

    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version="s3v4"),
    )

    upload_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=600,
    )

    public_url = public_media_url(settings, key)
    return {"upload_url": upload_url, "public_url": public_url, "key": key}


def _s3_client(settings: Settings):
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(signature_version="s3v4"),
    )


def s3_key_from_image_url(settings: Settings, image_url: str) -> str | None:
    """CloudFront/S3 공개 URL → S3 object key."""
    raw = image_url.strip()
    if raw.startswith("/media/"):
        return None
    if raw.startswith("/"):
        return None
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    path = urlparse(raw).path.lstrip("/")
    return path or None


def is_owned_media_url(settings: Settings, image_url: str) -> bool:
    """우리 S3/CloudFront 또는 로컬 /media 만 True (외부 Figma URL 등은 False)."""
    if image_url.startswith("/media/"):
        return True
    if not settings.s3_enabled or not settings.cloudfront_url:
        return False

    raw = image_url.strip()
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"

    cf_host = urlparse(public_media_url(settings, f"{settings.s3_key_prefix.strip('/')}/x")).netloc.lower()
    if urlparse(raw).netloc.lower() != cf_host:
        return False

    prefix = settings.s3_key_prefix.strip("/")
    path = urlparse(raw).path.lstrip("/")
    return path.startswith(f"{prefix}/") if prefix else bool(path)


def delete_media_file(settings: Settings, image_url: str | None) -> None:
    """후보 이미지 삭제 (로컬 /media 또는 S3). 실패해도 예외를 밖으로 던지지 않음."""
    if not image_url or not is_owned_media_url(settings, image_url):
        return

    try:
        if image_url.startswith("/media/"):
            local = settings.media_path / image_url.removeprefix("/media/").lstrip("/")
            if local.is_file():
                local.unlink()
            return

        if not settings.s3_enabled:
            return

        key = s3_key_from_image_url(settings, image_url)
        if not key:
            return

        _s3_client(settings).delete_object(Bucket=settings.s3_bucket, Key=key)
    except Exception:
        logger.exception("Failed to delete media file: %s", image_url)
