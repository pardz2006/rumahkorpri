"""Iteration 12 backend tests:
- 5 new consumer logins (consumer2..6) with correct city/province
- Bank cleanup: bankdki2/3 must 401; btn@ and bankdki@ still work; isolation intact
- Regression: 12 projects / 49 units; 2 real KPR apps persist; dev isolation
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://rumah-deps.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, password):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)


# --- 5 NEW consumer logins ---
NEW_CONSUMERS = [
    ("consumer2@rumahkorpri.com", "Tangerang", "Banten"),
    ("consumer3@rumahkorpri.com", "Palangka Raya", "Kalimantan Tengah"),
    ("consumer4@rumahkorpri.com", "Bandar Lampung", "Lampung"),
    ("consumer5@rumahkorpri.com", "Semarang", "Jawa Tengah"),
    ("consumer6@rumahkorpri.com", "Medan", "Sumatera Utara"),
]


@pytest.mark.parametrize("email,city,province", NEW_CONSUMERS)
def test_new_consumer_login(email, city, province):
    r = _login(email, "consumer123")
    assert r.status_code == 200, f"{email} login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and data["token"]
    u = data["user"]
    assert u["role"] == "consumer"
    assert u["email"] == email
    assert u.get("city") == city, f"{email} city={u.get('city')}"
    assert u.get("province") == province, f"{email} province={u.get('province')}"


# --- Bank cleanup ---
def test_bankdki2_deleted():
    r = _login("bankdki2@rumahkorpri.com", "dki123")
    assert r.status_code == 401, f"bankdki2 unexpectedly returned {r.status_code}"


def test_bankdki3_deleted():
    r = _login("bankdki3@rumahkorpri.com", "dki123")
    assert r.status_code == 401, f"bankdki3 unexpectedly returned {r.status_code}"


def test_btn_still_works():
    r = _login("btn@rumahkorpri.com", "btn123")
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "btn_evaluator"


def test_bankdki_still_works():
    r = _login("bankdki@rumahkorpri.com", "dki123")
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "btn_evaluator"


# --- Isolation ---
def _auth_headers(email, password):
    tok = _login(email, password).json()["token"]
    return {"Authorization": f"Bearer {tok}"}


def test_kpr_isolation_btn_vs_dki():
    btn_h = _auth_headers("btn@rumahkorpri.com", "btn123")
    dki_h = _auth_headers("bankdki@rumahkorpri.com", "dki123")
    btn_apps = requests.get(f"{API}/kpr/applications", headers=btn_h, timeout=30)
    dki_apps = requests.get(f"{API}/kpr/applications", headers=dki_h, timeout=30)
    assert btn_apps.status_code == 200
    assert dki_apps.status_code == 200
    btn_list = btn_apps.json()
    dki_list = dki_apps.json()
    for a in btn_list:
        assert a.get("bank") == "Bank BTN", f"BTN saw non-BTN app: {a.get('bank')}"
    for a in dki_list:
        assert a.get("bank") == "Bank DKI", f"DKI saw non-DKI app: {a.get('bank')}"


def test_cross_bank_patch_forbidden():
    btn_h = _auth_headers("btn@rumahkorpri.com", "btn123")
    dki_h = _auth_headers("bankdki@rumahkorpri.com", "dki123")
    # get a DKI app id (if any)
    dki_apps = requests.get(f"{API}/kpr/applications", headers=dki_h, timeout=30).json()
    if not dki_apps:
        pytest.skip("No DKI apps to test cross-bank patch")
    aid = dki_apps[0]["id"]
    r = requests.patch(f"{API}/kpr/applications/{aid}",
                       headers=btn_h, json={"status": "approved"}, timeout=30)
    assert r.status_code == 403, f"expected 403 cross-bank, got {r.status_code}"


# --- Regression ---
def test_projects_count():
    r = requests.get(f"{API}/projects", timeout=30)
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) == 12, f"expected 12 projects, got {len(projects)}"


def test_units_count():
    r = requests.get(f"{API}/projects", timeout=30)
    projects = r.json()
    total_units = 0
    for p in projects:
        detail = requests.get(f"{API}/projects/{p['id']}", timeout=30)
        assert detail.status_code == 200
        total_units += len(detail.json().get("units", []))
    assert total_units == 49, f"expected 49 units, got {total_units}"


def test_kpr_apps_persist():
    btn_h = _auth_headers("btn@rumahkorpri.com", "btn123")
    dki_h = _auth_headers("bankdki@rumahkorpri.com", "dki123")
    btn_apps = requests.get(f"{API}/kpr/applications", headers=btn_h, timeout=30).json()
    dki_apps = requests.get(f"{API}/kpr/applications", headers=dki_h, timeout=30).json()
    assert len(btn_apps) >= 1, "expected at least 1 BTN app"
    assert len(dki_apps) >= 1, "expected at least 1 DKI app"
    btn_statuses = [a.get("status") for a in btn_apps]
    dki_statuses = [a.get("status") for a in dki_apps]
    assert "pre_approved" in btn_statuses, f"BTN statuses: {btn_statuses}"
    assert "pending" in dki_statuses, f"DKI statuses: {dki_statuses}"


def test_developer_isolation():
    dev4_h = _auth_headers("developer4@rumahkorpri.com", "developer123")
    projects = requests.get(f"{API}/projects", timeout=30).json()
    # find a project NOT belonging to dev4
    dev4_projects = requests.get(f"{API}/developer/projects", headers=dev4_h, timeout=30)
    if dev4_projects.status_code != 200:
        pytest.skip(f"developer/projects endpoint returned {dev4_projects.status_code}")
    dev4_ids = {p["id"] for p in dev4_projects.json()}
    foreign = next((p for p in projects if p["id"] not in dev4_ids), None)
    if not foreign:
        pytest.skip("No foreign project")
    r = requests.put(f"{API}/developer/projects/{foreign['id']}", headers=dev4_h,
                     json={"name": "hack"}, timeout=30)
    assert r.status_code == 403, f"expected 403, got {r.status_code}"
