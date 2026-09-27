import os
import uuid
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import logging
import asyncio
import hmac
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from bson import ObjectId
import base64

from db import db, clean
import auth
from auth import get_current_user, require_roles, get_optional_user
import kpr
from spr import generate_spr_pdf
from receipt import generate_receipt_pdf
from kpr_pdf import generate_kpr_pdf
from whatsapp import send_whatsapp, is_enabled as wa_enabled
from seed import seed, DOC_TYPES
from storage import init_storage, store_media, get_object
from geo import coords_for_location

app = FastAPI(title="Rumah KORPRI API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rumahkorpri")


# ---------------- helpers ----------------
async def notify(user_id: str, title: str, message: str, kind: str = "info"):
    await db.notifications.insert_one({
        "user_id": user_id, "title": title, "message": message,
        "kind": kind, "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


async def wa_log(booking_id: str | None, phone: str, template: str, message: str,
                 recipient_name: str = ""):
    result = await asyncio.to_thread(send_whatsapp, phone, message)
    await db.wa_logs.insert_one({
        "booking_id": booking_id, "phone": phone, "recipient_name": recipient_name,
        "template": template, "message": message,
        "status": result["status"],
        "channel": "simulasi" if result["simulated"] else "twilio",
        "provider_sid": result["sid"],
        "error": result["error"],
        "read": False,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })
    return result


def wa_template(name: str, ctx: dict) -> str:
    templates = {
        "spr_issued": (
            "Halo {name} 👋\nSelamat! Surat Pemesanan Rumah (SPR) Anda untuk unit "
            "{unit} di {project} telah TERBIT. Nomor SPR: {spr}. "
            "Dokumen PDF telah dikirim ke email Anda. Tim Bank BTN akan segera memproses kelayakan KPR Anda."
        ),
        "doc_reminder": (
            "Halo {name} 👋\nPengajuan KPR Anda untuk unit {unit} di {project} masih menunggu kelengkapan dokumen: "
            "{missing}. Silakan unggah melalui tautan berikut tanpa perlu login rumit:\n{link}\n"
            "Terima kasih 🙏 — CRM Rumah KORPRI"
        ),
        "payment_confirmed": (
            "Halo {name} 👋\nPembayaran booking fee sebesar {fee} untuk unit {unit} telah kami TERIMA. "
            "SPR Anda sedang diproses oleh developer."
        ),
        "dp_confirmed": (
            "Halo {name} 👋\nPembayaran uang muka (DP) sebesar {fee} untuk unit {unit} telah kami TERIMA. "
            "Proses akad KPR akan segera dijadwalkan bersama Bank BTN."
        ),
        "kpr_status": (
            "Halo {name} 👋\nStatus pengajuan KPR Anda kini: {status}. {note}"
        ),
        "dp_due_reminder": (
            "Halo {name} 👋\nPengingat: cicilan Uang Muka (DP) Termin ke-{termin} sebesar {amount} "
            "untuk unit {unit} akan JATUH TEMPO pada {due}. Mohon segera lakukan pembayaran melalui portal. "
            "Terima kasih 🙏 — CRM Rumah KORPRI"
        ),
    }
    return templates.get(name, "{msg}").format(**{k: ctx.get(k, "-") for k in
        ["name", "unit", "project", "spr", "missing", "link", "fee", "status", "note",
         "msg", "termin", "amount", "due"]})


def rupiah(v):
    try:
        return "Rp " + f"{int(v):,}".replace(",", ".")
    except Exception:
        return f"Rp {v}"


# Jatuh tempo tiap termin DP (hari sejak SPR terbit): termin 1, 2, 3.
DP_DUE_OFFSETS = [14, 30, 60]


def make_dp_termins(dp_amount: float, n: int = 3):
    base = round(dp_amount / n)
    termins = []
    for i in range(1, n + 1):
        amt = base if i < n else dp_amount - base * (n - 1)
        termins.append({"no": i, "amount": amt, "status": "pending", "ref": None, "paid_at": None})
    return termins


def store_media_or_400(value, subdir):
    try:
        return store_media(value, subdir)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------- KPR simulate (public) ----------------
class SimInput(BaseModel):
    price: float
    dp_percent: float = 10
    tenor_years: int = 15
    program: str = "FLPP"


@api.post("/kpr/simulate")
async def kpr_simulate(inp: SimInput):
    return kpr.simulate(inp.price, inp.dp_percent, inp.tenor_years, inp.program)


@api.post("/kpr/amortization")
async def kpr_amortization(inp: SimInput):
    return kpr.amortization_schedule(inp.price, inp.dp_percent, inp.tenor_years, inp.program)


@api.post("/kpr/simulate/pdf")
async def kpr_simulate_pdf(inp: SimInput):
    data = kpr.amortization_schedule(inp.price, inp.dp_percent, inp.tenor_years, inp.program)
    pdf = generate_kpr_pdf(data)
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=simulasi-kpr.pdf"},
    )


@api.get("/kpr/programs")
async def kpr_programs():
    return kpr.PROGRAMS


# ---------------- saved simulations (consumer) ----------------
class SaveSimInput(BaseModel):
    price: float
    dp_percent: float = 10
    tenor_years: int = 15
    program: str = "FLPP"
    label: str | None = None


@api.post("/simulations")
async def save_simulation(inp: SaveSimInput, user: dict = Depends(get_current_user)):
    r = kpr.simulate(inp.price, inp.dp_percent, inp.tenor_years, inp.program)
    amo = kpr.amortization_schedule(inp.price, inp.dp_percent, inp.tenor_years, inp.program)
    doc = {
        "user_id": user["id"],
        "share_token": uuid.uuid4().hex,
        "label": (inp.label or "").strip() or f"{r['program_label']} · {rupiah(inp.price)}",
        "price": inp.price,
        "dp_percent": inp.dp_percent,
        "dp_amount": r["dp_amount"],
        "tenor_years": inp.tenor_years,
        "program": r["program"],
        "program_label": r["program_label"],
        "loan_amount": r["loan_amount"],
        "first_installment": r["first_installment"],
        "schedule": r["schedule"],
        "total_interest": amo["total_interest"],
        "total_paid": amo["total_paid"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.simulations.insert_one(doc)
    saved = await db.simulations.find_one({"_id": res.inserted_id})
    return clean(saved)


@api.get("/simulations")
async def list_simulations(user: dict = Depends(get_current_user)):
    sims = [clean(s) async for s in
            db.simulations.find({"user_id": user["id"]}).sort("created_at", -1)]
    return sims


@api.delete("/simulations/{sim_id}")
async def delete_simulation(sim_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(sim_id)
    except Exception:
        raise HTTPException(404, "Simulasi tidak ditemukan")
    res = await db.simulations.delete_one({"_id": oid, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(404, "Simulasi tidak ditemukan")
    return {"ok": True}


@api.post("/simulations/{sim_id}/share")
async def share_simulation(sim_id: str, user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(sim_id)
    except Exception:
        raise HTTPException(404, "Simulasi tidak ditemukan")
    sim = await db.simulations.find_one({"_id": oid, "user_id": user["id"]})
    if not sim:
        raise HTTPException(404, "Simulasi tidak ditemukan")
    token = sim.get("share_token")
    if not token:
        token = uuid.uuid4().hex
        await db.simulations.update_one({"_id": oid}, {"$set": {"share_token": token}})
    return {"share_token": token, "path": f"/s/{token}"}


@api.get("/public/simulations/{token}")
async def public_simulation(token: str):
    sim = await db.simulations.find_one({"share_token": token})
    if not sim:
        raise HTTPException(404, "Simulasi tidak ditemukan")
    owner = None
    if sim.get("user_id"):
        try:
            owner = await db.users.find_one({"_id": ObjectId(sim["user_id"])})
        except Exception:
            owner = None
    sim = clean(sim)
    sim.pop("user_id", None)
    sim["shared_by"] = owner.get("name") if owner else None
    return sim


# ---------------- profile (domisili) ----------------
class ProfileUpdate(BaseModel):
    phone: str | None = None
    city: str | None = None
    province: str | None = None
    instansi: str | None = None
    monthly_income: float | None = None


@api.patch("/profile")
async def update_profile(inp: ProfileUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in inp.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": updates})
    fresh = await db.users.find_one({"_id": ObjectId(user["id"])})
    return clean(fresh)


# ---------------- projects & units (public) ----------------
def _domicile_score(p: dict, city: str, province: str) -> int:
    """Skor relevansi domisili: +2 jika kota cocok, +1 jika provinsi cocok."""
    haystack = ((p.get("location") or "") + " " + (p.get("address_detail") or "")).lower()
    score = 0
    if city and city in haystack:
        score += 2
    if province and province in haystack:
        score += 1
    return score


@api.get("/projects")
async def list_projects(request: Request):
    hidden_devs = {str(u["_id"]) async for u in
                   db.users.find({"role": "admin_developer", "hidden": True}, {"_id": 1})}
    projects = [clean(p) async for p in db.projects.find().sort("created_at", 1)
                if p.get("developer_id") not in hidden_devs]
    for p in projects:
        units = [clean(u) async for u in db.units.find({"project_id": p["id"]})]
        p["units"] = units
        p["available_count"] = sum(1 for u in units if u["status"] == "available")
        p["total_units"] = len(units)
    # Urutkan: proyek di kota domisili user dulu, lalu satu provinsi, sisanya.
    user = await get_optional_user(request)
    if user and (user.get("city") or user.get("province")):
        city = (user.get("city") or "").strip().lower()
        province = (user.get("province") or "").strip().lower()
        for p in projects:
            p["match_score"] = _domicile_score(p, city, province)
        projects.sort(key=lambda p: p.get("match_score", 0), reverse=True)
    return projects


@api.get("/projects/{project_id}")
async def get_project(project_id: str):
    p = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not p:
        raise HTTPException(404, "Proyek tidak ditemukan")
    dev = await db.users.find_one({"_id": ObjectId(p["developer_id"])}) if p.get("developer_id") else None
    if dev and dev.get("hidden"):
        raise HTTPException(404, "Proyek tidak tersedia")
    p = clean(p)
    p["units"] = [clean(u) async for u in db.units.find({"project_id": project_id})]
    return p


# ---------------- developer: project & unit management ----------------
async def _assert_project_owner(project: dict, user: dict):
    """admin_korpri melihat semua; developer hanya proyek miliknya sendiri."""
    if user["role"] == "admin_korpri":
        return
    if project.get("developer_id") != user["id"]:
        raise HTTPException(403, "Anda hanya dapat mengelola produk milik sendiri")


async def _owned_project_ids(user: dict):
    """None berarti akses penuh (admin_korpri). Selain itu daftar id proyek milik user."""
    if user["role"] == "admin_korpri":
        return None
    return [str(p["_id"]) async for p in
            db.projects.find({"developer_id": user["id"]}, {"_id": 1})]


class ProjectCreateInput(BaseModel):
    name: str
    location: str
    address_detail: str | None = None
    developer_name: str | None = None
    description: str | None = None
    image: str | None = None
    program: str = "KOMERSIAL"
    bank: str | None = None
    lat: float | None = None
    lng: float | None = None


class UnitCreateInput(BaseModel):
    project_id: str
    type: str
    block: str
    number: str
    price: float
    land_area: float | None = None
    building_area: float | None = None
    address_detail: str | None = None
    image_front: str | None = None
    image_layout: str | None = None
    image_siteplan: str | None = None
    image_location_map: str | None = None
    gps_coordinates: str | None = None
    videos: list[str] | None = None
    gallery: list[str] | None = None


@api.get("/developer/projects")
async def developer_projects(user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    q = {} if user["role"] == "admin_korpri" else {"developer_id": user["id"]}
    projects = [clean(p) async for p in db.projects.find(q).sort("created_at", 1)]
    for p in projects:
        units = [clean(u) async for u in db.units.find({"project_id": p["id"]})]
        p["units"] = units
        p["available_count"] = sum(1 for u in units if u["status"] == "available")
        p["total_units"] = len(units)
    return projects


@api.post("/developer/projects")
async def create_project(inp: ProjectCreateInput,
                         user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    if inp.program not in ("FLPP", "KOMERSIAL"):
        raise HTTPException(400, "Program harus FLPP atau KOMERSIAL")
    if inp.image and len(inp.image) > 8_000_000:
        raise HTTPException(400, "Ukuran gambar terlalu besar (maks ~6 MB)")
    doc = inp.model_dump()
    doc["image"] = store_media_or_400(doc.get("image"), "projects")
    doc["developer_id"] = user["id"]
    if not doc.get("developer_name"):
        doc["developer_name"] = user.get("company") or user.get("name")
    if doc.get("lat") is None or doc.get("lng") is None:
        lat, lng = coords_for_location(doc.get("location", ""))
        doc["lat"], doc["lng"] = lat, lng
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.projects.insert_one(doc)

    # Notifikasi Unit Baru: beri tahu peminat yang berdomisili di kota proyek ini.
    city = (doc.get("location") or "").split(",")[0].strip()
    if city:
        async for c in db.users.find({"role": "consumer"}):
            if (c.get("city") or "").strip().lower() == city.lower():
                await notify(str(c["_id"]), "Proyek baru di kota Anda 🏠",
                             f"{doc['name']} kini tersedia di {city}. Lihat unit & simulasikan KPR sekarang.",
                             "info")

    return clean(await db.projects.find_one({"_id": res.inserted_id}))


class ProjectUpdateInput(BaseModel):
    name: str | None = None
    location: str | None = None
    address_detail: str | None = None
    developer_name: str | None = None
    description: str | None = None
    image: str | None = None
    program: str | None = None
    bank: str | None = None


@api.put("/developer/projects/{project_id}")
async def update_project(project_id: str, inp: ProjectUpdateInput,
                         user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    p = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not p:
        raise HTTPException(404, "Proyek tidak ditemukan")
    await _assert_project_owner(p, user)
    updates = {k: v for k, v in inp.model_dump().items() if v is not None}
    if "program" in updates and updates["program"] not in ("FLPP", "KOMERSIAL"):
        raise HTTPException(400, "Program harus FLPP atau KOMERSIAL")
    if "image" in updates:
        if len(updates["image"]) > 8_000_000:
            raise HTTPException(400, "Ukuran gambar terlalu besar (maks ~6 MB)")
        updates["image"] = store_media_or_400(updates["image"], "projects")
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.projects.update_one({"_id": p["_id"]}, {"$set": updates})
        if "name" in updates:
            await db.units.update_many({"project_id": project_id},
                                       {"$set": {"project_name": updates["name"]}})
    return clean(await db.projects.find_one({"_id": p["_id"]}))


@api.post("/developer/units")
async def create_unit(inp: UnitCreateInput,
                      user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    p = await db.projects.find_one({"_id": ObjectId(inp.project_id)})
    if not p:
        raise HTTPException(404, "Proyek tidak ditemukan")
    await _assert_project_owner(p, user)
    for img in (inp.image_front, inp.image_layout, inp.image_siteplan):
        if img and len(img) > 8_000_000:
            raise HTTPException(400, "Ukuran gambar terlalu besar (maks ~6 MB per foto)")
    dup = await db.units.find_one({"project_id": inp.project_id,
                                   "block": inp.block.upper(), "number": inp.number})
    if dup:
        raise HTTPException(400, f"Unit Blok {inp.block}/{inp.number} sudah ada di proyek ini")
    doc = inp.model_dump()
    doc["block"] = inp.block.upper()
    doc["image_front"] = store_media_or_400(doc.get("image_front"), "units")
    doc["image_layout"] = store_media_or_400(doc.get("image_layout"), "units")
    doc["image_siteplan"] = store_media_or_400(doc.get("image_siteplan"), "units")
    doc["image_location_map"] = store_media_or_400(doc.get("image_location_map"), "units")
    doc["gallery"] = [store_media_or_400(g, "units") for g in (doc.get("gallery") or [])]
    doc["project_name"] = p["name"]
    doc["status"] = "available"
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.units.insert_one(doc)
    return clean(await db.units.find_one({"_id": res.inserted_id}))


class UnitBulkCreateInput(UnitCreateInput):
    number: str | None = None  # ignored for bulk; range drives numbering
    start_number: int = 1
    count: int = 5
    number_prefix: str = ""
    number_pad: int = 2


@api.post("/developer/units/bulk")
async def create_units_bulk(inp: UnitBulkCreateInput,
                            user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    p = await db.projects.find_one({"_id": ObjectId(inp.project_id)})
    if not p:
        raise HTTPException(404, "Proyek tidak ditemukan")
    await _assert_project_owner(p, user)
    if inp.count < 1 or inp.count > 50:
        raise HTTPException(400, "Jumlah unit harus antara 1 dan 50")
    for img in (inp.image_front, inp.image_layout, inp.image_siteplan, inp.image_location_map):
        if img and len(img) > 8_000_000:
            raise HTTPException(400, "Ukuran gambar terlalu besar (maks ~6 MB per foto)")

    block = inp.block.upper()
    numbers = [f"{inp.number_prefix}{str(inp.start_number + i).zfill(inp.number_pad)}"
               for i in range(inp.count)]
    existing = {u["number"] async for u in
                db.units.find({"project_id": inp.project_id, "block": block}, {"number": 1})}
    clash = [n for n in numbers if n in existing]
    if clash:
        raise HTTPException(400, f"Nomor sudah ada di Blok {block}: {', '.join(clash)}")

    # Upload shared media once, reuse served paths across all units.
    shared = {
        "image_front": store_media_or_400(inp.image_front, "units"),
        "image_layout": store_media_or_400(inp.image_layout, "units"),
        "image_siteplan": store_media_or_400(inp.image_siteplan, "units"),
        "image_location_map": store_media_or_400(inp.image_location_map, "units"),
        "gallery": [store_media_or_400(g, "units") for g in (inp.gallery or [])],
    }
    now = datetime.now(timezone.utc).isoformat()
    docs = []
    for n in numbers:
        docs.append({
            "project_id": inp.project_id, "project_name": p["name"],
            "type": inp.type, "block": block, "number": n, "price": inp.price,
            "land_area": inp.land_area, "building_area": inp.building_area,
            "address_detail": inp.address_detail, "gps_coordinates": inp.gps_coordinates,
            "videos": inp.videos or [],
            **shared, "status": "available", "created_at": now,
        })
    result = await db.units.insert_many(docs)
    return {"ok": True, "created": len(result.inserted_ids), "numbers": numbers}


class UnitImportInput(BaseModel):
    project_id: str
    file_name: str
    file_data: str  # base64 data URL or raw base64 of CSV/XLSX


UNIT_IMPORT_COLUMNS = ["type", "block", "number", "price",
                       "land_area", "building_area", "address_detail", "gps_coordinates"]


@api.post("/developer/units/import")
async def import_units(inp: UnitImportInput,
                       user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    import io
    import pandas as pd

    p = await db.projects.find_one({"_id": ObjectId(inp.project_id)})
    if not p:
        raise HTTPException(404, "Proyek tidak ditemukan")
    await _assert_project_owner(p, user)

    raw = inp.file_data.partition(",")[2] if inp.file_data.startswith("data:") else inp.file_data
    try:
        data = base64.b64decode(raw)
    except Exception:
        raise HTTPException(400, "File tidak dapat dibaca")

    name = (inp.file_name or "").lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(data))
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(data))
        else:
            try:
                df = pd.read_csv(io.BytesIO(data))
            except Exception:
                df = pd.read_excel(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(400, f"Gagal membaca file: {e}")

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    if "type" not in df.columns or "block" not in df.columns or "number" not in df.columns or "price" not in df.columns:
        raise HTTPException(400, "Kolom wajib tidak ada: type, block, number, price")

    existing = {(u["block"], str(u["number"])) async for u in
                db.units.find({"project_id": inp.project_id}, {"block": 1, "number": 1})}
    now = datetime.now(timezone.utc).isoformat()
    docs, errors, seen = [], [], set()

    def num(v):
        try:
            return float(v) if pd.notna(v) and str(v).strip() != "" else None
        except Exception:
            return None

    for i, row in df.iterrows():
        line = i + 2  # header is row 1
        block = str(row.get("block", "")).strip().upper()
        number = str(row.get("number", "")).strip()
        if number.endswith(".0"):
            number = number[:-2]
        type_ = str(row.get("type", "")).strip()
        price = num(row.get("price"))
        if not block or not number or not type_ or price is None:
            errors.append(f"Baris {line}: type/block/number/price wajib diisi"); continue
        key = (block, number)
        if key in existing or key in seen:
            errors.append(f"Baris {line}: Blok {block}/{number} duplikat"); continue
        seen.add(key)
        docs.append({
            "project_id": inp.project_id, "project_name": p["name"],
            "type": type_, "block": block, "number": number, "price": price,
            "land_area": num(row.get("land_area")), "building_area": num(row.get("building_area")),
            "address_detail": (str(row.get("address_detail")).strip()
                               if pd.notna(row.get("address_detail")) else None),
            "gps_coordinates": (str(row.get("gps_coordinates")).strip()
                                if pd.notna(row.get("gps_coordinates")) else None),
            "image_front": None, "image_layout": None, "image_siteplan": None,
            "image_location_map": None, "gallery": [], "videos": [],
            "status": "available", "created_at": now,
        })

    created = 0
    if docs:
        res = await db.units.insert_many(docs)
        created = len(res.inserted_ids)
    return {"ok": True, "created": created, "errors": errors, "total_rows": int(len(df))}


class UnitUpdateInput(BaseModel):
    type: str | None = None
    block: str | None = None
    number: str | None = None
    price: float | None = None
    land_area: float | None = None
    building_area: float | None = None
    address_detail: str | None = None
    image_front: str | None = None
    image_layout: str | None = None
    image_siteplan: str | None = None
    image_location_map: str | None = None
    gps_coordinates: str | None = None
    videos: list[str] | None = None
    gallery: list[str] | None = None


@api.put("/developer/units/{unit_id}")
async def update_unit(unit_id: str, inp: UnitUpdateInput,
                      user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    u = await db.units.find_one({"_id": ObjectId(unit_id)})
    if not u:
        raise HTTPException(404, "Unit tidak ditemukan")
    proj = await db.projects.find_one({"_id": ObjectId(u["project_id"])})
    if proj:
        await _assert_project_owner(proj, user)
    updates = {k: v for k, v in inp.model_dump().items() if v is not None}
    if "block" in updates:
        updates["block"] = updates["block"].upper()
    new_block = updates.get("block", u["block"])
    new_number = updates.get("number", u["number"])
    if (new_block, new_number) != (u["block"], u["number"]):
        dup = await db.units.find_one({"project_id": u["project_id"],
                                       "block": new_block, "number": new_number,
                                       "_id": {"$ne": u["_id"]}})
        if dup:
            raise HTTPException(400, f"Unit Blok {new_block}/{new_number} sudah ada di proyek ini")
    for field in ("image_front", "image_layout", "image_siteplan", "image_location_map"):
        if field in updates:
            if len(updates[field]) > 8_000_000:
                raise HTTPException(400, "Ukuran gambar terlalu besar (maks ~6 MB per foto)")
            updates[field] = store_media_or_400(updates[field], "units")
    if "gallery" in updates:
        updates["gallery"] = [store_media_or_400(g, "units") for g in (updates["gallery"] or [])]
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.units.update_one({"_id": u["_id"]}, {"$set": updates})
    return clean(await db.units.find_one({"_id": u["_id"]}))


@api.delete("/developer/units/{unit_id}")
async def delete_unit(unit_id: str,
                      user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    u = await db.units.find_one({"_id": ObjectId(unit_id)})
    if not u:
        raise HTTPException(404, "Unit tidak ditemukan")
    proj = await db.projects.find_one({"_id": ObjectId(u["project_id"])})
    if proj:
        await _assert_project_owner(proj, user)
    active = await db.bookings.find_one({"unit_id": unit_id})
    if u.get("status") != "available" or active:
        raise HTTPException(400, "Unit sudah dipesan/terjual dan tidak dapat dihapus")
    await db.units.delete_one({"_id": u["_id"]})
    return {"ok": True}


# ---------------- bookings ----------------
class BookingInput(BaseModel):
    unit_id: str
    program: str = "FLPP"
    dp_percent: float = 10
    tenor_years: int = 15
    payment_method: str = "QRIS"  # QRIS | VA_BTN


BOOKING_FEE = 5000000


@api.post("/bookings")
async def create_booking(inp: BookingInput, user: dict = Depends(require_roles("consumer"))):
    unit = await db.units.find_one({"_id": ObjectId(inp.unit_id)})
    if not unit:
        raise HTTPException(404, "Unit tidak ditemukan")
    if unit["status"] != "available":
        raise HTTPException(400, "Unit tidak tersedia untuk dipesan")

    sim = kpr.simulate(unit["price"], inp.dp_percent, inp.tenor_years, inp.program)
    va_number = "8898" + str(uuid.uuid4().int)[:12]
    booking = {
        "user_id": user["id"],
        "unit_id": inp.unit_id,
        "project_id": unit["project_id"],
        "program": inp.program,
        "dp_percent": inp.dp_percent,
        "tenor_years": inp.tenor_years,
        "kpr_sim": sim,
        "booking_fee": BOOKING_FEE,
        "dp_amount": sim["dp_amount"],
        "dp_termins": make_dp_termins(sim["dp_amount"]),
        "dp_paid_amount": 0,
        "dp_payment_status": "pending",   # pending | partial | paid
        "payment_method": inp.payment_method,
        "payment_status": "pending",   # pending | paid | failed
        "va_number": va_number,
        "qris_payload": "00020101021126" + va_number,
        "payment_ref": None,
        "spr_status": "not_ready",     # not_ready | draft | approved | issued
        "spr_number": None,
        "spr_pdf": None,
        "signature": None,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.bookings.insert_one(booking)
    await db.units.update_one({"_id": ObjectId(inp.unit_id)}, {"$set": {"status": "booked"}})
    # simpan simulasi pemesanan otomatis ke riwayat peminat
    amo = kpr.amortization_schedule(unit["price"], inp.dp_percent, inp.tenor_years, inp.program)
    await db.simulations.insert_one({
        "user_id": user["id"],
        "share_token": uuid.uuid4().hex,
        "label": f"{unit['type']} · {unit.get('project_name') or 'Proyek'} (pesanan)",
        "price": unit["price"],
        "dp_percent": inp.dp_percent,
        "dp_amount": sim["dp_amount"],
        "tenor_years": inp.tenor_years,
        "program": sim["program"],
        "program_label": sim["program_label"],
        "loan_amount": sim["loan_amount"],
        "first_installment": sim["first_installment"],
        "schedule": sim["schedule"],
        "total_interest": amo["total_interest"],
        "total_paid": amo["total_paid"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await notify(user["id"], "Pemesanan dibuat",
                 f"Silakan bayar booking fee {rupiah(BOOKING_FEE)} untuk unit {unit['type']}.", "info")
    b = await db.bookings.find_one({"_id": res.inserted_id})
    return clean(b)


async def _enrich(b: dict) -> dict:
    b = clean(b)
    unit = await db.units.find_one({"_id": ObjectId(b["unit_id"])})
    project = await db.projects.find_one({"_id": ObjectId(b["project_id"])})
    u = await db.users.find_one({"_id": ObjectId(b["user_id"])})
    b["unit"] = clean(unit) if unit else None
    b["project"] = clean(project) if project else None
    b["consumer"] = clean(u) if u else None
    b["documents"] = [clean(d) async for d in db.documents.find({"booking_id": b["id"]})]
    b.pop("spr_pdf", None)  # keep list responses light
    # backfill DP termin schedule for legacy bookings
    if b.get("dp_amount") and not b.get("dp_termins"):
        termins = make_dp_termins(b["dp_amount"])
        await db.bookings.update_one({"_id": ObjectId(b["id"])},
                                     {"$set": {"dp_termins": termins, "dp_paid_amount": 0}})
        b["dp_termins"] = termins
        b["dp_paid_amount"] = 0
    # backfill due dates once SPR issued
    if b.get("spr_status") == "issued" and b.get("dp_termins") and \
       any(not t.get("due_date") for t in b["dp_termins"]):
        base = b.get("spr_issued_at")
        start = datetime.fromisoformat(base) if base else datetime.now(timezone.utc)
        for t, off in zip(b["dp_termins"], DP_DUE_OFFSETS):
            t.setdefault("reminded", False)
            if not t.get("due_date"):
                t["due_date"] = (start + timedelta(days=off)).isoformat()
        await db.bookings.update_one({"_id": ObjectId(b["id"])},
                                     {"$set": {"dp_termins": b["dp_termins"]}})
    return b


@api.get("/bookings")
async def list_bookings(user: dict = Depends(get_current_user)):
    q = {}
    if user["role"] == "consumer":
        q = {"user_id": user["id"]}
    bookings = [b async for b in db.bookings.find(q).sort("created_at", -1)]
    return [await _enrich(b) for b in bookings]


@api.get("/bookings/{booking_id}")
async def get_booking(booking_id: str, user: dict = Depends(get_current_user)):
    b = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not b:
        raise HTTPException(404, "Pemesanan tidak ditemukan")
    if user["role"] == "consumer" and b["user_id"] != user["id"]:
        raise HTTPException(403, "Akses ditolak")
    return await _enrich(b)


# ---------------- payment (simulated QRIS/VA + webhook) ----------------
@api.post("/bookings/{booking_id}/pay")
async def initiate_payment(booking_id: str, user: dict = Depends(require_roles("consumer"))):
    b = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not b:
        raise HTTPException(404, "Pemesanan tidak ditemukan")
    return {
        "booking_id": booking_id,
        "method": b["payment_method"],
        "amount": b["booking_fee"],
        "va_number": b["va_number"],
        "qris_payload": b["qris_payload"],
        "instructions": "Simulasi: klik 'Konfirmasi Pembayaran' untuk memicu webhook verifikasi.",
    }


class WebhookInput(BaseModel):
    booking_id: str
    status: str = "paid"  # simulated gateway status
    kind: str = "booking_fee"  # booking_fee | dp_termin
    termin_no: int | None = None


@api.post("/bookings/{booking_id}/pay-dp")
async def initiate_dp(booking_id: str, termin_no: int = 1,
                      user: dict = Depends(require_roles("consumer"))):
    b = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not b:
        raise HTTPException(404, "Pemesanan tidak ditemukan")
    if b["user_id"] != user["id"]:
        raise HTTPException(403, "Akses ditolak")
    if b.get("spr_status") != "issued":
        raise HTTPException(400, "SPR belum terbit, DP belum bisa dibayar")
    termins = b.get("dp_termins") or make_dp_termins(b.get("dp_amount", 0))
    termin = next((t for t in termins if t["no"] == termin_no), None)
    if not termin:
        raise HTTPException(404, "Termin tidak ditemukan")
    if termin["status"] == "paid":
        raise HTTPException(400, f"Termin {termin_no} sudah dibayar")
    unpaid_before = [t for t in termins if t["no"] < termin_no and t["status"] != "paid"]
    if unpaid_before:
        raise HTTPException(400, f"Selesaikan termin ke-{unpaid_before[0]['no']} terlebih dahulu")
    return {
        "booking_id": booking_id,
        "kind": "dp_termin",
        "termin_no": termin_no,
        "method": b["payment_method"],
        "amount": termin["amount"],
        "va_number": b["va_number"],
        "qris_payload": b["qris_payload"],
        "instructions": "Simulasi: klik 'Konfirmasi Pembayaran' untuk memicu verifikasi termin DP.",
    }


@api.post("/payments/webhook")
async def payment_webhook(inp: WebhookInput):
    """Simulated payment gateway webhook (QRIS/VA BTN)."""
    b = await db.bookings.find_one({"_id": ObjectId(inp.booking_id)})
    if not b:
        raise HTTPException(404, "Pemesanan tidak ditemukan")
    ref = "PAY-" + str(uuid.uuid4())[:8].upper()

    if inp.status != "paid":
        await db.bookings.update_one({"_id": b["_id"]},
                                     {"$set": {"payment_status": "failed", "payment_ref": ref}})
        return {"ok": True, "ref": ref}

    u = await db.users.find_one({"_id": ObjectId(b["user_id"])})
    unit = await db.units.find_one({"_id": ObjectId(b["unit_id"])})

    if inp.kind == "dp_termin":
        termins = b.get("dp_termins") or make_dp_termins(b.get("dp_amount", 0))
        target = next((t for t in termins if t["no"] == inp.termin_no), None)
        if not target or target["status"] == "paid":
            raise HTTPException(400, "Termin tidak valid atau sudah dibayar")
        unpaid_before = [t for t in termins if t["no"] < inp.termin_no and t["status"] != "paid"]
        if unpaid_before:
            raise HTTPException(400, f"Termin ke-{unpaid_before[0]['no']} harus dibayar lebih dahulu")
        target["status"] = "paid"; target["ref"] = ref
        target["paid_at"] = datetime.now(timezone.utc).isoformat()
        paid_amount = sum(t["amount"] for t in termins if t["status"] == "paid")
        all_paid = all(t["status"] == "paid" for t in termins)
        dp_status = "paid" if all_paid else ("partial" if paid_amount > 0 else "pending")
        await db.bookings.update_one({"_id": b["_id"]}, {"$set": {
            "dp_termins": termins, "dp_paid_amount": paid_amount, "dp_payment_status": dp_status,
        }})
        remaining = b.get("dp_amount", 0) - paid_amount
        title = "DP Lunas 🎉" if all_paid else f"Termin DP ke-{inp.termin_no} diterima"
        msg = (f"Pembayaran termin ke-{inp.termin_no} sebesar {rupiah(target['amount'])} diterima (Ref {ref}). "
               + ("Seluruh uang muka telah LUNAS." if all_paid else f"Sisa DP: {rupiah(remaining)}."))
        await notify(b["user_id"], title, msg, "success")
        await wa_log(str(b["_id"]), u.get("phone", "-"), "dp_confirmed",
                     wa_template("dp_confirmed", {
                         "name": u["name"], "unit": unit["type"], "fee": rupiah(target["amount"])}),
                     u["name"])
        return {"ok": True, "ref": ref, "dp_payment_status": dp_status, "remaining": remaining}

    # booking fee -> generate SPR draft
    spr_number = "SPR/" + datetime.now().strftime("%Y%m") + "/" + str(uuid.uuid4().int)[:5]
    await db.bookings.update_one({"_id": b["_id"]}, {"$set": {
        "payment_status": "paid", "payment_ref": ref,
        "spr_status": "draft", "spr_number": spr_number, "status": "paid",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }})
    await notify(b["user_id"], "Pembayaran terverifikasi",
                 f"Booking fee diterima (Ref {ref}). SPR sedang diproses developer.", "success")
    await wa_log(str(b["_id"]), u.get("phone", "-"), "payment_confirmed",
                 wa_template("payment_confirmed", {
                     "name": u["name"], "unit": unit["type"], "fee": rupiah(b["booking_fee"])}),
                 u["name"])
    return {"ok": True, "ref": ref}


# ---------------- developer: SPR approval ----------------
class SprApproveInput(BaseModel):
    signature: str | None = None  # base64 data URL of signature/stamp


@api.get("/developer/spr-queue")
async def spr_queue(user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    q = {"spr_status": {"$in": ["draft", "approved", "issued"]}}
    owned = await _owned_project_ids(user)
    if owned is not None:
        q["project_id"] = {"$in": owned}
    bookings = [b async for b in db.bookings.find(q).sort("created_at", -1)]
    return [await _enrich(b) for b in bookings]


@api.post("/bookings/{booking_id}/spr/approve")
async def approve_spr(booking_id: str, inp: SprApproveInput,
                      user: dict = Depends(require_roles("admin_developer", "admin_korpri"))):
    b = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not b:
        raise HTTPException(404, "Pemesanan tidak ditemukan")
    if b["payment_status"] != "paid":
        raise HTTPException(400, "Booking fee belum dibayar")

    unit = await db.units.find_one({"_id": ObjectId(b["unit_id"])})
    project = await db.projects.find_one({"_id": ObjectId(b["project_id"])})
    u = await db.users.find_one({"_id": ObjectId(b["user_id"])})
    if project:
        await _assert_project_owner(project, user)

    pdf_b64 = generate_spr_pdf(b, clean(unit), clean(project), clean(u), inp.signature)
    await db.bookings.update_one({"_id": b["_id"]}, {"$set": {
        "spr_status": "issued", "signature": inp.signature, "spr_pdf": pdf_b64,
        "status": "spr_issued",
        "spr_issued_at": datetime.now(timezone.utc).isoformat(),
    }})
    await db.units.update_one({"_id": unit["_id"]}, {"$set": {"status": "sold"}})

    # Auto-create KPR application forwarded to BTN
    if not await db.kpr_applications.find_one({"booking_id": booking_id}):
        await db.kpr_applications.insert_one({
            "booking_id": booking_id,
            "user_id": b["user_id"],
            "unit_id": b["unit_id"],
            "project_id": b["project_id"],
            "loan_amount": b["kpr_sim"]["loan_amount"],
            "program": b["program"],
            "bank": (project or {}).get("bank") or "Bank BTN",
            "status": "pending",   # pending | pre_approved | approved | rejected | need_revision
            "slik_note": None,
            "evaluator_note": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Seed document checklist for this booking
    for dt in DOC_TYPES:
        if not await db.documents.find_one({"booking_id": booking_id, "doc_type": dt}):
            await db.documents.insert_one({
                "booking_id": booking_id, "user_id": b["user_id"], "doc_type": dt,
                "file_data": None, "file_name": None,
                "status": "missing",  # missing | uploaded | valid | invalid
                "note": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    await notify(b["user_id"], "SPR terbit 🎉",
                 f"SPR {b['spr_number']} telah diterbitkan. Lengkapi dokumen KPR Anda.", "success")
    await wa_log(booking_id, u.get("phone", "-"), "spr_issued",
                 wa_template("spr_issued", {"name": u["name"], "unit": unit["type"],
                                            "project": project["name"], "spr": b["spr_number"]}),
                 u["name"])
    return await _enrich(await db.bookings.find_one({"_id": b["_id"]}))


@api.get("/bookings/{booking_id}/spr.pdf")
async def download_spr(booking_id: str):
    b = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not b or not b.get("spr_pdf"):
        raise HTTPException(404, "SPR belum tersedia")
    data = base64.b64decode(b["spr_pdf"])
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{b.get("spr_number","SPR")}.pdf"'})


# ---------------- documents ----------------
class DocUploadInput(BaseModel):
    doc_type: str
    file_data: str  # base64 data url
    file_name: str


@api.post("/bookings/{booking_id}/documents")
async def upload_document(booking_id: str, inp: DocUploadInput,
                          user: dict = Depends(get_current_user)):
    b = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not b:
        raise HTTPException(404, "Pemesanan tidak ditemukan")
    doc = await db.documents.find_one({"booking_id": booking_id, "doc_type": inp.doc_type})
    payload = {"file_data": inp.file_data, "file_name": inp.file_name,
               "status": "uploaded", "note": None,
               "uploaded_at": datetime.now(timezone.utc).isoformat()}
    if doc:
        await db.documents.update_one({"_id": doc["_id"]}, {"$set": payload})
    else:
        payload.update({"booking_id": booking_id, "user_id": b["user_id"],
                        "doc_type": inp.doc_type,
                        "created_at": datetime.now(timezone.utc).isoformat()})
        await db.documents.insert_one(payload)
    return {"ok": True}


class DocVerifyInput(BaseModel):
    status: str  # valid | invalid
    note: str | None = None


@api.patch("/documents/{doc_id}/verify")
async def verify_document(doc_id: str, inp: DocVerifyInput,
                          user: dict = Depends(require_roles("admin_korpri", "admin_developer"))):
    d = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not d:
        raise HTTPException(404, "Dokumen tidak ditemukan")
    await db.documents.update_one({"_id": d["_id"]},
                                  {"$set": {"status": inp.status, "note": inp.note}})
    await notify(d["user_id"], "Verifikasi dokumen",
                 f"Dokumen {d['doc_type']} berstatus: {inp.status.upper()}."
                 + (f" Catatan: {inp.note}" if inp.note else ""),
                 "success" if inp.status == "valid" else "warning")
    return {"ok": True}


@api.get("/documents/{doc_id}/file")
async def get_document_file(doc_id: str, user: dict = Depends(get_current_user)):
    d = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not d or not d.get("file_data"):
        raise HTTPException(404, "File tidak ada")
    return {"file_name": d.get("file_name"), "file_data": d["file_data"]}


# ---------------- CRM follow-up (WhatsApp automation) ----------------
@api.post("/bookings/{booking_id}/followup")
async def send_followup(booking_id: str, user: dict = Depends(require_roles("admin_korpri"))):
    b = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    if not b:
        raise HTTPException(404, "Pemesanan tidak ditemukan")
    docs = [d async for d in db.documents.find({"booking_id": booking_id})]
    missing = [d["doc_type"] for d in docs if d["status"] in ("missing", "invalid")]
    if not missing:
        raise HTTPException(400, "Semua dokumen sudah lengkap/valid")
    unit = await db.units.find_one({"_id": ObjectId(b["unit_id"])})
    project = await db.projects.find_one({"_id": ObjectId(b["project_id"])})
    u = await db.users.find_one({"_id": ObjectId(b["user_id"])})
    link = f"https://rumahkorpri.com/upload/{booking_id}"
    msg = wa_template("doc_reminder", {
        "name": u["name"], "unit": unit["type"], "project": project["name"],
        "missing": ", ".join(missing), "link": link})
    wa = await wa_log(booking_id, u.get("phone", "-"), "doc_reminder", msg, u["name"])
    await notify(b["user_id"], "Pengingat dokumen",
                 f"Mohon lengkapi dokumen: {', '.join(missing)}.", "warning")
    return {"ok": True, "missing": missing, "message": msg,
            "channel": "simulasi" if wa["simulated"] else "twilio",
            "wa_status": wa["status"], "wa_error": wa["error"]}


# ---------------- BTN: KPR applications ----------------
@api.get("/kpr/applications")
async def kpr_applications(user: dict = Depends(require_roles("btn_evaluator", "admin_korpri"))):
    q = {}
    if user["role"] == "btn_evaluator":
        q["bank"] = user.get("bank")
    apps = [a async for a in db.kpr_applications.find(q).sort("created_at", -1)]
    out = []
    for a in apps:
        a = clean(a)
        b = await db.bookings.find_one({"_id": ObjectId(a["booking_id"])})
        a["booking"] = await _enrich(b) if b else None
        out.append(a)
    return out


class KprStatusInput(BaseModel):
    status: str  # pre_approved | approved | rejected | need_revision
    evaluator_note: str | None = None
    slik_note: str | None = None


@api.patch("/kpr/applications/{app_id}")
async def update_kpr_status(app_id: str, inp: KprStatusInput,
                            user: dict = Depends(require_roles("btn_evaluator"))):
    a = await db.kpr_applications.find_one({"_id": ObjectId(app_id)})
    if not a:
        raise HTTPException(404, "Pengajuan tidak ditemukan")
    if user["role"] == "btn_evaluator" and a.get("bank") != user.get("bank"):
        raise HTTPException(403, "Pengajuan ini ditujukan ke bank lain")
    await db.kpr_applications.update_one({"_id": a["_id"]}, {"$set": {
        "status": inp.status, "evaluator_note": inp.evaluator_note,
        "slik_note": inp.slik_note,
        "updated_at": datetime.now(timezone.utc).isoformat()}})
    labels = {"pre_approved": "Pra-Disetujui", "approved": "Disetujui",
              "rejected": "Ditolak", "need_revision": "Perlu Revisi"}
    u = await db.users.find_one({"_id": ObjectId(a["user_id"])})
    await notify(a["user_id"], "Status KPR diperbarui",
                 f"Pengajuan KPR Anda: {labels.get(inp.status, inp.status)}."
                 + (f" {inp.evaluator_note}" if inp.evaluator_note else ""),
                 "success" if inp.status in ("approved", "pre_approved") else "warning")
    await wa_log(a["booking_id"], u.get("phone", "-"), "kpr_status",
                 wa_template("kpr_status", {"name": u["name"],
                             "status": labels.get(inp.status, inp.status),
                             "note": inp.evaluator_note or ""}), u["name"])
    return {"ok": True}


# ---------------- admin: user management (superuser) ----------------
def _require_superuser(user: dict):
    if user.get("role") != "admin_korpri" or not user.get("is_superuser"):
        raise HTTPException(403, "Hanya Super Admin KORPRI yang dapat mengelola pengguna")


class AdminCreateUserInput(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # consumer | admin_developer | btn_evaluator
    phone: str | None = None
    company: str | None = None   # wajib utk admin_developer
    bank: str | None = None      # wajib utk btn_evaluator
    nik: str | None = None
    instansi: str | None = None
    monthly_income: float | None = None
    city: str | None = None
    province: str | None = None


@api.get("/admin/users")
async def admin_list_users(user: dict = Depends(require_roles("admin_korpri"))):
    _require_superuser(user)
    return [clean(u) async for u in db.users.find().sort("created_at", 1)]


@api.post("/admin/users")
async def admin_create_user(inp: AdminCreateUserInput,
                            user: dict = Depends(require_roles("admin_korpri"))):
    _require_superuser(user)
    if inp.role not in ("consumer", "admin_developer", "btn_evaluator"):
        raise HTTPException(400, "Peran harus consumer, admin_developer, atau btn_evaluator")
    if inp.role == "admin_developer" and not (inp.company or "").strip():
        raise HTTPException(400, "Nama perusahaan wajib untuk Developer")
    if inp.role == "btn_evaluator" and not (inp.bank or "").strip():
        raise HTTPException(400, "Nama bank wajib untuk Analis Bank")
    email = inp.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email sudah terdaftar")
    doc = {
        "name": inp.name, "email": email, "role": inp.role,
        "phone": inp.phone, "company": inp.company, "bank": inp.bank,
        "nik": inp.nik, "instansi": inp.instansi, "monthly_income": inp.monthly_income,
        "city": inp.city, "province": inp.province, "is_superuser": False,
        "password_hash": auth.hash_password(inp.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.users.insert_one(doc)
    return clean(await db.users.find_one({"_id": res.inserted_id}))


class AdminUpdateUserInput(BaseModel):
    name: str | None = None
    role: str | None = None
    phone: str | None = None
    company: str | None = None
    bank: str | None = None
    city: str | None = None
    province: str | None = None
    password: str | None = None


class AdminStatusInput(BaseModel):
    disabled: bool


class AdminVisibilityInput(BaseModel):
    hidden: bool


async def _get_managed_user(user_id: str):
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(404, "Pengguna tidak ditemukan")
    if target.get("is_superuser"):
        raise HTTPException(403, "Akun Super Admin tidak dapat diubah dari sini")
    return target


@api.put("/admin/users/{user_id}")
async def admin_update_user(user_id: str, inp: AdminUpdateUserInput,
                            user: dict = Depends(require_roles("admin_korpri"))):
    _require_superuser(user)
    await _get_managed_user(user_id)
    updates = {k: v for k, v in inp.model_dump().items() if v is not None and k != "password"}
    if inp.role and inp.role not in ("consumer", "admin_developer", "btn_evaluator"):
        raise HTTPException(400, "Peran tidak valid")
    if inp.password:
        if len(inp.password) < 6:
            raise HTTPException(400, "Kata sandi minimal 6 karakter")
        updates["password_hash"] = auth.hash_password(inp.password)
    if updates:
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    return clean(await db.users.find_one({"_id": ObjectId(user_id)}))


@api.patch("/admin/users/{user_id}/status")
async def admin_set_user_status(user_id: str, inp: AdminStatusInput,
                                user: dict = Depends(require_roles("admin_korpri"))):
    _require_superuser(user)
    await _get_managed_user(user_id)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"disabled": inp.disabled}})
    return clean(await db.users.find_one({"_id": ObjectId(user_id)}))


@api.patch("/admin/users/{user_id}/visibility")
async def admin_set_user_visibility(user_id: str, inp: AdminVisibilityInput,
                                    user: dict = Depends(require_roles("admin_korpri"))):
    _require_superuser(user)
    target = await _get_managed_user(user_id)
    if target.get("role") != "admin_developer":
        raise HTTPException(400, "Hanya akun Developer yang memiliki produk untuk disembunyikan")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"hidden": inp.hidden}})
    return clean(await db.users.find_one({"_id": ObjectId(user_id)}))


@api.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, user: dict = Depends(require_roles("admin_korpri"))):
    _require_superuser(user)
    if user_id == user["id"]:
        raise HTTPException(400, "Anda tidak dapat menghapus akun sendiri")
    await _get_managed_user(user_id)
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"ok": True}
@api.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user)):
    return [clean(n) async for n in
            db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).limit(50)]


@api.post("/notifications/{notif_id}/read")
async def read_notification(notif_id: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one({"_id": ObjectId(notif_id)}, {"$set": {"read": True}})
    return {"ok": True}


@api.get("/wa-logs")
async def get_wa_logs(user: dict = Depends(require_roles("admin_korpri", "admin_developer"))):
    return [clean(w) async for w in db.wa_logs.find().sort("sent_at", -1).limit(100)]


@api.get("/whatsapp/status")
async def whatsapp_status(user: dict = Depends(require_roles("admin_korpri", "admin_developer"))):
    return {"enabled": wa_enabled(), "channel": "twilio" if wa_enabled() else "simulasi"}


class WaTestInput(BaseModel):
    phone: str
    message: str | None = None


@api.post("/whatsapp/test")
async def whatsapp_test(inp: WaTestInput, user: dict = Depends(require_roles("admin_korpri"))):
    if not wa_enabled():
        raise HTTPException(400, "Kredensial Twilio belum dikonfigurasi (mode simulasi).")
    body = inp.message or "Tes koneksi WhatsApp rumahkorpri.com — integrasi Twilio aktif ✅"
    result = await asyncio.to_thread(send_whatsapp, inp.phone, body)
    return result


# ---------------- cron: pengingat DP jatuh tempo ----------------
@api.post("/cron/dp-reminders")
async def cron_dp_reminders(request: Request):
    """Dipanggil oleh scheduler harian. Kirim pengingat WhatsApp untuk termin DP
    yang jatuh tempo dalam <= 3 hari (atau sudah lewat) dan belum diingatkan."""
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=3)
    reminded = 0
    cursor = db.bookings.find({"spr_status": "issued", "dp_termins": {"$exists": True}})
    async for b in cursor:
        termins = b.get("dp_termins") or []
        changed = False
        due_termins = []
        for t in termins:
            if t.get("status") == "paid" or t.get("reminded"):
                continue
            due = t.get("due_date")
            if not due:
                continue
            try:
                due_dt = datetime.fromisoformat(due)
            except Exception:
                continue
            if due_dt <= horizon:
                due_termins.append((t, due_dt))
        if not due_termins:
            continue
        u = await db.users.find_one({"_id": ObjectId(b["user_id"])})
        unit = await db.units.find_one({"_id": ObjectId(b["unit_id"])})
        for t, due_dt in due_termins:
            msg = wa_template("dp_due_reminder", {
                "name": u.get("name", "-") if u else "-",
                "unit": unit.get("type", "-") if unit else "-",
                "termin": t.get("no"),
                "amount": rupiah(t.get("amount", 0)),
                "due": due_dt.strftime("%d %b %Y"),
            })
            await wa_log(str(b["_id"]), (u or {}).get("phone", "-"),
                         "dp_due_reminder", msg, (u or {}).get("name", ""))
            t["reminded"] = True
            reminded += 1
            changed = True
            if u:
                await notify(b["user_id"], "Pengingat DP jatuh tempo",
                             f"Termin ke-{t.get('no')} ({rupiah(t.get('amount', 0))}) jatuh tempo {due_dt.strftime('%d %b %Y')}.",
                             "warning")
        if changed:
            await db.bookings.update_one({"_id": b["_id"]}, {"$set": {"dp_termins": termins}})
    return {"ok": True, "reminded": reminded}


# ---------------- dashboard stats ----------------
@api.get("/stats")
async def stats(user: dict = Depends(require_roles("admin_korpri", "admin_developer", "btn_evaluator"))):
    booking_q, unit_q = {}, {}
    if user["role"] == "admin_developer":
        owned = await _owned_project_ids(user)
        booking_q["project_id"] = {"$in": owned or []}
        unit_q["project_id"] = {"$in": owned or []}
    kpr_q = {}
    if user["role"] == "btn_evaluator":
        kpr_q["bank"] = user.get("bank")
    total_bookings = await db.bookings.count_documents(booking_q)
    paid = await db.bookings.count_documents({**booking_q, "payment_status": "paid"})
    spr_issued = await db.bookings.count_documents({**booking_q, "spr_status": "issued"})
    units_available = await db.units.count_documents({**unit_q, "status": "available"})
    units_sold = await db.units.count_documents({**unit_q, "status": "sold"})
    kpr_pending = await db.kpr_applications.count_documents({**kpr_q, "status": "pending"})
    kpr_approved = await db.kpr_applications.count_documents({**kpr_q, "status": "approved"})
    docs_missing = await db.documents.count_documents({"status": {"$in": ["missing", "invalid"]}})
    return {
        "total_bookings": total_bookings, "paid_bookings": paid,
        "spr_issued": spr_issued, "units_available": units_available,
        "units_sold": units_sold, "kpr_pending": kpr_pending,
        "kpr_approved": kpr_approved, "docs_missing": docs_missing,
    }


@api.get("/files/{path:path}")
async def serve_media(path: str):
    try:
        data, ctype = get_object(path)
    except Exception:
        raise HTTPException(404, "File tidak ditemukan")
    return Response(content=data, media_type=ctype)


@api.get("/")
async def root():
    return {"message": "Rumah KORPRI API aktif"}


app.include_router(auth.router)
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    try:
        init_storage()
        logger.info("Object storage terinisialisasi")
    except Exception as e:
        logger.error(f"Storage init gagal: {e}")
    await seed()
    logger.info("Seed selesai")


@app.on_event("shutdown")
async def on_shutdown():
    from db import client
    client.close()
