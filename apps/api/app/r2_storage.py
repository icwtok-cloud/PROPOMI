"""Cloudflare R2 — subida de fotos de propiedades (agencias).

Variables de entorno (Render):
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
  R2_ENDPOINT, R2_BUCKET, R2_PUBLIC_BASE_URL

El crawler NO usa este módulo: sigue con URLs externas de los portales.
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

# boto3 es opcional en import: si falta, el endpoint responde 503 claro.
try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
    _BOTO_OK = True
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore
    Config = None  # type: ignore
    BotoCoreError = ClientError = Exception  # type: ignore
    _BOTO_OK = False

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_BYTES = 3 * 1024 * 1024  # 3 MB


def r2_configured() -> bool:
    keys = (
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_ENDPOINT",
        "R2_BUCKET",
        "R2_PUBLIC_BASE_URL",
    )
    return _BOTO_OK and all(os.getenv(k) for k in keys)


def _client():
    if not r2_configured():
        raise RuntimeError("R2 no configurado o boto3 no instalado")
    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"].rstrip("/"),
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def public_url_for_key(key: str) -> str:
    base = os.environ["R2_PUBLIC_BASE_URL"].rstrip("/")
    return f"{base}/{key.lstrip('/')}"


def upload_property_image(
    *,
    agency_id: str,
    property_id: str,
    data: bytes,
    content_type: str,
) -> str:
    """Sube bytes al bucket y devuelve la URL pública."""
    if not data:
        raise ValueError("archivo vacío")
    if len(data) > MAX_BYTES:
        raise ValueError(f"archivo supera {MAX_BYTES // (1024 * 1024)} MB")
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct not in ALLOWED_CONTENT_TYPES:
        raise ValueError("solo jpeg, png o webp")
    ext = ALLOWED_CONTENT_TYPES[ct]
    key = f"agencies/{agency_id}/{property_id}/{uuid.uuid4().hex}.{ext}"
    bucket = os.environ["R2_BUCKET"]
    try:
        _client().put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=ct,
            CacheControl="public, max-age=31536000",
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"R2 put_object falló: {exc}") from exc
    return public_url_for_key(key)


def delete_by_public_url(url: str) -> bool:
    """Best-effort delete si la URL es de nuestro bucket público."""
    base = os.environ.get("R2_PUBLIC_BASE_URL", "").rstrip("/")
    if not base or not url.startswith(base + "/"):
        return False
    key = url[len(base) + 1 :]
    try:
        _client().delete_object(Bucket=os.environ["R2_BUCKET"], Key=key)
        return True
    except Exception:
        return False
