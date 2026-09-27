"""Isi field kosong pada unit contoh: siteplan, peta lokasi, GPS, galeri, video, alamat.
Unit di Palangka Raya milik PT Steven Pengharapan Sejati (data real) tidak diubah.
Idempotent — aman dijalankan berulang."""
import os
from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]

SITEPLANS = [
    "https://images.unsplash.com/photo-1494380982332-dfc36fbfece6?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1491357492920-d2979986a84e?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1506092309076-af15fb0051e3?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1498141321056-776a06214e24?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
]
MAPS = [
    "https://images.unsplash.com/photo-1713456959045-729452fdafe4?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1708958310998-90223b478216?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1760904730849-a61076f615a6?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1627797341872-7694d02573f4?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
]
INTERIORS = [
    "https://images.unsplash.com/photo-1649083048770-82e8ffd80431?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1724582586529-62622e50c0b3?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1724582586495-d050726cf354?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
    "https://images.unsplash.com/photo-1724582586458-a51791349977?crop=entropy&cs=srgb&fm=jpg&q=85&w=1080",
]
VIDEOS = [
    "https://www.youtube.com/watch?v=TTVJQOsSwpE",
    "https://www.youtube.com/watch?v=DKAy5Fdb1kQ",
    "https://www.youtube.com/watch?v=rZGkt4dyLt4",
    "https://www.youtube.com/watch?v=jsjX0r4GEEU",
]

updated = skipped = 0
for pi, p in enumerate(db.projects.find()):
    loc = (p.get("location") or "").lower()
    dev = (p.get("developer_name") or "").lower()
    pid = str(p["_id"])
    if "palangka" in loc or "steven" in dev:
        skipped += db.units.count_documents({"project_id": pid})
        continue
    sp = SITEPLANS[pi % len(SITEPLANS)]
    mp = MAPS[pi % len(MAPS)]
    lat0, lng0 = p.get("lat"), p.get("lng")
    for u in db.units.find({"project_id": pid}):
        bi = max(ord((u.get("block") or "A")[0].upper()) - 65, 0)
        try:
            ni = int(u.get("number") or 0)
        except ValueError:
            ni = 0
        idx = bi * 37 + ni
        gps = None
        if lat0 is not None and lng0 is not None:
            lat = round(lat0 - bi * 0.00045 - ni * 0.00006, 6)
            lng = round(lng0 + ni * 0.00035 + bi * 0.00008, 6)
            gps = f"{lat}, {lng}"
        addr = f"Blok {u.get('block')} No. {u.get('number')}, {p.get('address_detail') or p.get('name')}, {p.get('location')}"
        db.units.update_one({"_id": u["_id"]}, {"$set": {
            "image_siteplan": sp,
            "image_location_map": mp,
            "gps_coordinates": gps,
            "gallery": [INTERIORS[idx % 4], INTERIORS[(idx + 1) % 4], INTERIORS[(idx + 2) % 4]],
            "videos": [VIDEOS[idx % 4]],
            "address_detail": addr,
        }})
        updated += 1

print(f"updated={updated} skipped={skipped}")
for f in ["image_front", "image_layout", "image_siteplan", "image_location_map",
          "gps_coordinates", "gallery", "videos", "address_detail"]:
    n = db.units.count_documents({"$or": [{f: None}, {f: ""}, {f: []}, {f: {"$exists": False}}]})
    print(f"masih kosong {f}: {n}")
