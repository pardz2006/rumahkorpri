import os
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def oid(v) -> str:
    return str(v)


def clean(doc: dict) -> dict:
    """Convert a Mongo document into a JSON-safe dict (ObjectId -> str id)."""
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    doc.pop("password_hash", None)
    return doc


def to_object_id(v: str):
    return ObjectId(v)
