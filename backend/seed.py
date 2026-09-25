"""Seed demo users, projects and units on startup (idempotent, versioned)."""
import os
from datetime import datetime, timezone

from db import db
from auth import hash_password

DOC_TYPES = ["KTP", "NPWP", "Slip Gaji", "SPT Tahunan", "SK Pegawai", "Kartu Keluarga"]

# Bump to force a re-seed of projects/units (wipes demo catalog data only).
SEED_VERSION = 3

# House exterior photos (rotated across units).
EXT = [
    "https://images.unsplash.com/photo-1777115470242-9b21d2c67729?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1777115471024-b0a140087e60?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1774685109541-0bb9f759f880?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1759355787121-eaef014a501d?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1719887805632-de5be825f72b?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1706164971298-7d210902ec42?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1706164971302-e30c0640cc3b?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1706164971309-fb4785fe6ceb?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
]

# Floor-plan (denah) illustrations by building area — shows ruang tamu, kamar tidur, dll.
DENAH = {
    36: "https://static.prod-images.emergentagent.com/jobs/10bc8f43-0482-4cca-b2d5-96be43395cfc/images/51e3b8652526d6cbb99f9d2b72d8f4893670b7b0b748703529046ffc3ced6bf9.jpeg",
    45: "https://static.prod-images.emergentagent.com/jobs/10bc8f43-0482-4cca-b2d5-96be43395cfc/images/b267d779842c623829f6854e0ae906b0bdd02b63cdd3ee0500bceb9ad88b1f08.jpeg",
    60: "https://static.prod-images.emergentagent.com/jobs/10bc8f43-0482-4cca-b2d5-96be43395cfc/images/5618fca278237d2fe7511ea47114325f44c99296ae1ec93eba71feee5f78cc2c.jpeg",
    70: "https://static.prod-images.emergentagent.com/jobs/10bc8f43-0482-4cca-b2d5-96be43395cfc/images/886f6aa2d26a9d7f7d96eb986480d0e0f021857c95a247597db01e30702cb680.jpeg",
}


def _denah(building_area: float) -> str:
    return DENAH[min(DENAH.keys(), key=lambda k: abs(k - building_area))]


_ext_i = 0


def _unit(type_, block, number, price, lt, lb, status="available"):
    global _ext_i
    front = EXT[_ext_i % len(EXT)]
    _ext_i += 1
    return {
        "type": type_, "block": block, "number": number, "price": price,
        "land_area": lt, "building_area": lb, "status": status,
        "image_front": front, "image_layout": _denah(lb), "image_siteplan": None,
    }


async def seed():
    now = datetime.now(timezone.utc).isoformat()

    # ---- Users ----
    owner_email = os.environ.get("OWNER_EMAIL", "admin@rumahkorpri.com").lower()
    owner_pass = os.environ.get("OWNER_PASSWORD", "korpri123")

    users = [
        {"name": "Admin KORPRI", "email": owner_email, "role": "admin_korpri",
         "password": owner_pass, "phone": "081200000001"},
        {"name": "Admin KORPRI (Pardz)", "email": "pardz2006@gmail.com", "role": "admin_korpri",
         "password": "korpri123", "phone": "081200000005"},
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
            await db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {"password_hash": doc["password_hash"], "role": u["role"],
                          "city": u.get("city"), "province": u.get("province"),
                          "bank": u.get("bank"), "company": u.get("company")}},
            )

    # ---- Projects & Units (versioned re-seed) ----
    meta = await db.meta.find_one({"key": "seed_version"})
    current_version = meta["value"] if meta else 0
    if current_version >= SEED_VERSION:
        return

    # Wipe demo catalog + dependent demo records, then rebuild.
    for coll in ("projects", "units", "bookings", "kpr_applications",
                 "documents", "notifications", "wa_logs", "simulations"):
        await db[coll].delete_many({})

    dev1 = await db.users.find_one({"email": "developer@rumahkorpri.com"})
    dev2 = await db.users.find_one({"email": "developer2@rumahkorpri.com"})
    dev3 = await db.users.find_one({"email": "developer3@rumahkorpri.com"})

    def owner(dev):
        return {"developer_id": str(dev["_id"]), "developer_name": dev["company"]}

    projects = [
        # ---- Developer 1: PT Griya Sejahtera ----
        {
            **owner(dev1),
            "name": "Griya KORPRI Harmoni",
            "location": "Bekasi, Jawa Barat",
            "address_detail": "Jl. Harmoni Raya, Bekasi Timur",
            "description": "Perumahan bersubsidi khusus ASN dengan akses tol & fasilitas lengkap.",
            "image": EXT[4], "program": "FLPP", "bank": "Bank BTN",
            "units": [
                _unit("Tipe 36/72", "A", "01", 168000000, 72, 36),
                _unit("Tipe 36/72", "A", "02", 168000000, 72, 36),
                _unit("Tipe 36/84", "A", "03", 185000000, 84, 36, "booked"),
                _unit("Tipe 45/90", "B", "01", 232000000, 90, 45),
                _unit("Tipe 45/90", "B", "02", 232000000, 90, 45, "sold"),
                _unit("Tipe 45/96", "B", "03", 245000000, 96, 45),
            ],
        },
        {
            **owner(dev1),
            "name": "Bumi ASN Residence",
            "location": "Depok, Jawa Barat",
            "address_detail": "Jl. Margonda Residence, Depok",
            "description": "Hunian komersial modern strategis dekat stasiun & pusat kota.",
            "image": EXT[0], "program": "KOMERSIAL", "bank": "Bank DKI",
            "units": [
                _unit("Tipe 45/98", "C", "05", 485000000, 98, 45),
                _unit("Tipe 60/120", "C", "06", 720000000, 120, 60),
                _unit("Tipe 60/120", "D", "01", 735000000, 120, 60, "booked"),
                _unit("Tipe 70/140", "D", "02", 950000000, 140, 70),
                _unit("Tipe 70/150", "D", "03", 985000000, 150, 70),
            ],
        },
        # ---- Developer 2: PT Bumi Persada Nusantara ----
        {
            **owner(dev2),
            "name": "Persada Abdi Negara",
            "location": "Bogor, Jawa Barat",
            "address_detail": "Jl. Tegar Beriman, Cibinong, Bogor",
            "description": "Cluster subsidi ASN asri di kaki Gunung Salak, udara sejuk.",
            "image": EXT[5], "program": "FLPP", "bank": "Bank BTN",
            "units": [
                _unit("Tipe 36/66", "E", "01", 162000000, 66, 36),
                _unit("Tipe 36/72", "E", "02", 171000000, 72, 36),
                _unit("Tipe 36/72", "E", "03", 171000000, 72, 36),
                _unit("Tipe 45/84", "F", "01", 228000000, 84, 45, "booked"),
            ],
        },
        {
            **owner(dev2),
            "name": "Persada Grande Living",
            "location": "Tangerang Selatan, Banten",
            "address_detail": "Jl. BSD Boulevard, Serpong, Tangsel",
            "description": "Perumahan premium dengan klub renang, jogging track & smart home.",
            "image": EXT[2], "program": "KOMERSIAL", "bank": "Bank DKI",
            "units": [
                _unit("Tipe 60/112", "G", "01", 690000000, 112, 60),
                _unit("Tipe 60/120", "G", "02", 715000000, 120, 60),
                _unit("Tipe 70/144", "H", "01", 1025000000, 144, 70),
                _unit("Tipe 70/160", "H", "02", 1120000000, 160, 70, "sold"),
            ],
        },
        # ---- Developer 3: PT Karya Nyaman Sejahtera ----
        {
            **owner(dev3),
            "name": "Karya Nyaman Village",
            "location": "Bandung, Jawa Barat",
            "address_detail": "Jl. Soekarno-Hatta, Gedebage, Bandung",
            "description": "Rumah subsidi ASN dekat pusat teknopolis Bandung Timur.",
            "image": EXT[6], "program": "FLPP", "bank": "Bank BTN",
            "units": [
                _unit("Tipe 36/60", "J", "01", 158000000, 60, 36),
                _unit("Tipe 36/72", "J", "02", 169000000, 72, 36),
                _unit("Tipe 45/90", "K", "01", 236000000, 90, 45),
                _unit("Tipe 45/90", "K", "02", 236000000, 90, 45),
                _unit("Tipe 45/96", "K", "03", 249000000, 96, 45, "booked"),
            ],
        },
        {
            **owner(dev3),
            "name": "Nyaman Hills Premier",
            "location": "Bekasi, Jawa Barat",
            "address_detail": "Jl. Summarecon Boulevard, Bekasi Utara",
            "description": "Hunian komersial 2 lantai eksklusif dengan taman kota & danau buatan.",
            "image": EXT[1], "program": "KOMERSIAL", "bank": "Bank DKI",
            "units": [
                _unit("Tipe 60/120", "L", "01", 780000000, 120, 60),
                _unit("Tipe 70/150", "M", "01", 1080000000, 150, 70),
                _unit("Tipe 70/165", "M", "02", 1185000000, 165, 70),
                _unit("Tipe 70/180", "M", "03", 1290000000, 180, 70, "booked"),
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

    await db.meta.update_one({"key": "seed_version"},
                             {"$set": {"value": SEED_VERSION}}, upsert=True)
