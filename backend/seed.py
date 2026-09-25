"""Seed demo users, projects and units on startup (idempotent)."""
import os
from datetime import datetime, timezone

from db import db
from auth import hash_password

DOC_TYPES = ["KTP", "NPWP", "Slip Gaji", "SPT Tahunan", "SK Pegawai", "Kartu Keluarga"]


async def seed():
    now = datetime.now(timezone.utc).isoformat()

    # ---- Users ----
    owner_email = os.environ.get("OWNER_EMAIL", "admin@rumahkorpri.com").lower()
    owner_pass = os.environ.get("OWNER_PASSWORD", "korpri123")

    users = [
        {"name": "Admin KORPRI", "email": owner_email, "role": "admin_korpri",
         "password": owner_pass, "phone": "081200000001"},
        {"name": "Mitra Developer (Griya Sejahtera)", "email": "developer@rumahkorpri.com",
         "role": "admin_developer", "password": "developer123", "phone": "081200000002",
         "company": "PT Griya Sejahtera"},
        {"name": "Mitra Developer (Bumi Persada)", "email": "developer2@rumahkorpri.com",
         "role": "admin_developer", "password": "developer123", "phone": "081200000012",
         "company": "PT Bumi Persada Nusantara"},
        {"name": "Mitra Developer (Karya Nyaman)", "email": "developer3@rumahkorpri.com",
         "role": "admin_developer", "password": "developer123", "phone": "081200000013",
         "company": "PT Karya Nyaman Sejahtera"},
        {"name": "Analis Bank BTN", "email": "btn@rumahkorpri.com",
         "role": "btn_evaluator", "password": "btn123", "phone": "081200000003",
         "bank": "Bank BTN"},
        {"name": "Analis Bank DKI", "email": "bankdki@rumahkorpri.com",
         "role": "btn_evaluator", "password": "dki123", "phone": "081200000004",
         "bank": "Bank DKI"},
        {"name": "Budi Santoso (ASN)", "email": "consumer@rumahkorpri.com",
         "role": "consumer", "password": "consumer123", "phone": "081298765432",
         "nik": "3201011203900001", "instansi": "Kemendikbud", "monthly_income": 8500000,
         "city": "Bekasi", "province": "Jawa Barat"},
    ]
    for u in users:
        existing = await db.users.find_one({"email": u["email"]})
        doc = {
            "name": u["name"], "email": u["email"], "role": u["role"],
            "phone": u.get("phone"), "nik": u.get("nik"),
            "instansi": u.get("instansi"), "monthly_income": u.get("monthly_income"),
            "city": u.get("city"), "province": u.get("province"),
            "bank": u.get("bank"), "company": u.get("company"),
            "password_hash": hash_password(u["password"]), "created_at": now,
        }
        if not existing:
            await db.users.insert_one(doc)
        else:
            # keep password/role/profil in sync with seed
            await db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {"password_hash": doc["password_hash"], "role": u["role"],
                          "city": u.get("city"), "province": u.get("province"),
                          "bank": u.get("bank"), "company": u.get("company")}},
            )

    # ---- Projects & Units ----
    if await db.projects.count_documents({}) == 0:
        projects = [
            {
                "name": "Griya KORPRI Harmoni",
                "location": "Bekasi, Jawa Barat",
                "developer_name": "PT Griya Sejahtera",
                "description": "Perumahan bersubsidi khusus ASN dengan akses tol dan fasilitas lengkap.",
                "image": "https://images.pexels.com/photos/3918373/pexels-photo-3918373.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
                "program": "FLPP",
                "units": [
                    {"type": "Tipe 36/72", "block": "A", "number": "01", "price": 168000000, "land_area": 72, "building_area": 36, "status": "available"},
                    {"type": "Tipe 36/72", "block": "A", "number": "02", "price": 168000000, "land_area": 72, "building_area": 36, "status": "available"},
                    {"type": "Tipe 36/84", "block": "A", "number": "03", "price": 185000000, "land_area": 84, "building_area": 36, "status": "booked"},
                    {"type": "Tipe 45/90", "block": "B", "number": "01", "price": 232000000, "land_area": 90, "building_area": 45, "status": "available"},
                    {"type": "Tipe 45/90", "block": "B", "number": "02", "price": 232000000, "land_area": 90, "building_area": 45, "status": "sold"},
                ],
            },
            {
                "name": "Bumi ASN Residence",
                "location": "Depok, Jawa Barat",
                "developer_name": "PT Griya Sejahtera",
                "description": "Hunian komersial modern strategis dekat stasiun dan pusat kota.",
                "image": "https://images.unsplash.com/photo-1613553507747-5f8d62ad5904?crop=entropy&cs=srgb&fm=jpg&q=85",
                "program": "KOMERSIAL",
                "units": [
                    {"type": "Tipe 45/98", "block": "C", "number": "05", "price": 485000000, "land_area": 98, "building_area": 45, "status": "available"},
                    {"type": "Tipe 60/120", "block": "C", "number": "06", "price": 720000000, "land_area": 120, "building_area": 60, "status": "available"},
                    {"type": "Tipe 60/120", "block": "D", "number": "01", "price": 735000000, "land_area": 120, "building_area": 60, "status": "booked"},
                    {"type": "Tipe 70/140", "block": "D", "number": "02", "price": 950000000, "land_area": 140, "building_area": 70, "status": "available"},
                ],
            },
        ]
        for p in projects:
            units = p.pop("units")
            p["created_at"] = now
            res = await db.projects.insert_one(p)
            pid = str(res.inserted_id)
            for u in units:
                u["project_id"] = pid
                u["project_name"] = p["name"]
                u["created_at"] = now
                await db.units.insert_one(u)
