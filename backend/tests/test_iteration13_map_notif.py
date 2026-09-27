"""Iteration 13: map coords on projects + city-scoped new-project notification."""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://rumah-deps.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    j = r.json()
    return j["token"], j["user"]


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_projects_have_lat_lng():
    r = requests.get(f"{API}/projects", timeout=30)
    assert r.status_code == 200
    ps = r.json()
    assert len(ps) == 12, f"expected 12 projects, got {len(ps)}"
    missing = [p["name"] for p in ps if p.get("lat") is None or p.get("lng") is None]
    assert not missing, f"projects missing coords: {missing}"
    # Spot check Semarang coord
    sem = [p for p in ps if "Semarang" in (p.get("location") or "")]
    assert sem, "no Semarang project found"
    for p in sem:
        assert abs(p["lat"] - (-6.9932)) < 0.05
        assert abs(p["lng"] - 110.4203) < 0.05


def test_city_scoped_new_project_notification():
    # Baseline notif count for both consumers
    c5_tok, c5 = _login("consumer5@rumahkorpri.com", "consumer123")
    c1_tok, c1 = _login("consumer@rumahkorpri.com", "consumer123")
    assert (c5.get("city") or "").lower() == "semarang"
    # consumer@ is Bekasi
    assert "bekasi" in (c1.get("city") or "").lower()

    base_c5 = requests.get(f"{API}/notifications", headers=_hdr(c5_tok), timeout=30).json()
    base_c1 = requests.get(f"{API}/notifications", headers=_hdr(c1_tok), timeout=30).json()
    base_c5_ids = {n["id"] for n in base_c5}
    base_c1_ids = {n["id"] for n in base_c1}

    # Login as developer5 and create a Semarang project
    dev_tok, _ = _login("developer5@rumahkorpri.com", "developer123")
    payload = {
        "name": "TEST_MapNotifSemarang",
        "developer_name": "Harmoni Land Indonesia",
        "location": "Semarang, Jawa Tengah",
        "program": "KOMERSIAL",
        "description": "Test project for iteration 13 notification check",
        "total_units": 1,
    }
    r = requests.post(f"{API}/developer/projects", json=payload, headers=_hdr(dev_tok), timeout=30)
    assert r.status_code in (200, 201), f"create project failed: {r.status_code} {r.text}"
    proj = r.json()
    proj_id = proj.get("id") or proj.get("_id")
    assert proj_id
    assert proj.get("lat") is not None and proj.get("lng") is not None, "created project missing lat/lng"

    try:
        time.sleep(1)
        # consumer5 should get a new notification
        c5_now = requests.get(f"{API}/notifications", headers=_hdr(c5_tok), timeout=30).json()
        new_c5 = [n for n in c5_now if n["id"] not in base_c5_ids]
        assert new_c5, "consumer5 did NOT receive any new notification"
        titles = [n.get("title", "") for n in new_c5]
        assert any("Proyek baru" in t for t in titles), f"unexpected notif titles: {titles}"

        # consumer@ (Bekasi) must NOT receive the Semarang notification
        c1_now = requests.get(f"{API}/notifications", headers=_hdr(c1_tok), timeout=30).json()
        new_c1 = [n for n in c1_now if n["id"] not in base_c1_ids]
        semarang_leak = [n for n in new_c1 if "Semarang" in (n.get("message", "") + n.get("title", ""))
                         or "TEST_MapNotifSemarang" in (n.get("message", ""))]
        assert not semarang_leak, f"Bekasi consumer received Semarang notif: {semarang_leak}"
    finally:
        # Cleanup: delete the test project directly via MongoDB (no delete endpoint exists)
        try:
            from pymongo import MongoClient
            _c = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            _c[os.environ.get("DB_NAME", "test_database")].projects.delete_many(
                {"name": "TEST_MapNotifSemarang"}
            )
            _c.close()
        except Exception as _e:
            print("cleanup warn:", _e)
        # verify count back to 12
        ps = requests.get(f"{API}/projects", timeout=30).json()
        assert len(ps) == 12, f"cleanup failed; projects count = {len(ps)}"


def test_regression_catalog_counts():
    ps = requests.get(f"{API}/projects", timeout=30).json()
    assert len(ps) == 12
    total_units = sum(p.get("total_units", 0) for p in ps)
    assert total_units == 49, f"expected 49 units, got {total_units}"
