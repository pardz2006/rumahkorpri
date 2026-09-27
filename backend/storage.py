"""Emergent object storage integration for media (unit photos, project banners)."""
import os
import uuid
import base64

import requests

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "rumahkorpri"

MIME_EXT = {
    "image/jpeg": "jpg", "image/png": "png", "image/gif": "gif",
    "image/webp": "webp", "application/pdf": "pdf",
}

_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple[bytes, str]:
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def store_media(value: str | None, subdir: str) -> str | None:
    """Accepts a base64 data URL and uploads it, returning a served path `/api/files/{path}`.
    Passes through None, http(s) URLs and already-served `/api/files/...` paths unchanged.
    Rejects anything whose bytes are not a real JPEG/PNG/WebP image."""
    if not value:
        return value
    if not value.startswith("data:"):
        return value  # already a URL / served path
    header, _, b64 = value.partition(",")
    content_type = header.split(";")[0].replace("data:", "") or "image/png"
    data = base64.b64decode(b64)
    detected = _detect_image_type(data)
    if detected is None:
        raise ValueError("File bukan gambar yang valid (hanya JPG, PNG, WebP)")
    content_type, ext = detected
    path = f"{APP_NAME}/{subdir}/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, content_type)
    return "/api/files/" + result["path"]


def _detect_image_type(data: bytes):
    """Return (mime, ext) by inspecting magic bytes, or None if not a supported image."""
    if len(data) < 12:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ("image/png", "png")
    if data[:3] == b"\xff\xd8\xff":
        return ("image/jpeg", "jpg")
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("image/webp", "webp")
    return None
