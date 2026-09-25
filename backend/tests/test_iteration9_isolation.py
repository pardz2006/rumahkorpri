"""Iteration 9 isolation tests: developer/bank scoping + expanded seed catalog."""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://rumah-deps.preview.emergentagent.com"
API = f"{BASE}/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    j = r.json()
    return j.get("token") or j["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def tokens():
    return {
        "admin": _login("admin@rumahkorpri.com", "korpri123"),
        "dev1": _login("developer@rumahkorpri.com", "developer123"),
        "dev2": _login("developer2@rumahkorpri.com", "developer123"),
        "dev3": _login("developer3@rumahkorpri.com", "developer123"),
        "btn": _login("btn@rumahkorpri.com", "btn123"),
        "dki": _login("bankdki@rumahkorpri.com", "dki123"),
        "consumer": _login("consumer@rumahkorpri.com", "consumer123"),
    }


# ---- Public catalog ----
def test_public_projects_has_6_projects_and_28_units():
    r = requests.get(f"{API}/projects", timeout=30)
    assert r.status_code == 200
    projects = r.json()
    assert isinstance(projects, list)
    assert len(projects) == 6, f"expected 6 projects, got {len(projects)}: {[p.get('name') for p in projects]}"
    total_units = 0
    for p in projects:
        units = p.get("units", [])
        total_units += len(units)
        for unit in units:
            assert unit.get("image_front"), f"unit {unit.get('id')} missing image_front"
            assert unit.get("image_layout"), f"unit {unit.get('id')} missing image_layout"
    assert total_units == 28, f"expected 28 total units, got {total_units}"


# ---- Developer isolation ----
EXPECTED_DEV_PROJECTS = {
    "dev1": {"Griya KORPRI Harmoni", "Bumi ASN Residence"},
    "dev2": {"Persada Abdi Negara", "Persada Grande Living"},
    "dev3": {"Karya Nyaman Village", "Nyaman Hills Premier"},
}


@pytest.mark.parametrize("dev_key", ["dev1", "dev2", "dev3"])
def test_developer_scoped_projects(tokens, dev_key):
    r = requests.get(f"{API}/developer/projects", headers=_h(tokens[dev_key]), timeout=30)
    assert r.status_code == 200, r.text
    names = {p["name"] for p in r.json()}
    assert names == EXPECTED_DEV_PROJECTS[dev_key], f"{dev_key} sees {names}"


def test_admin_sees_all_projects(tokens):
    r = requests.get(f"{API}/developer/projects", headers=_h(tokens["admin"]), timeout=30)
    assert r.status_code == 200
    assert len(r.json()) == 6


# ---- Cross-developer 403 enforcement ----
def _dev_projects(token):
    r = requests.get(f"{API}/developer/projects", headers=_h(token), timeout=30)
    assert r.status_code == 200
    return r.json()


def test_dev1_cannot_update_dev2_project(tokens):
    dev2_projects = _dev_projects(tokens["dev2"])
    target = dev2_projects[0]
    r = requests.put(
        f"{API}/developer/projects/{target['id']}",
        headers=_h(tokens["dev1"]),
        json={"name": target["name"] + " HACKED"},
        timeout=30,
    )
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


def test_dev1_cannot_create_unit_in_dev2_project(tokens):
    dev2_projects = _dev_projects(tokens["dev2"])
    target = dev2_projects[0]
    payload = {
        "project_id": target["id"],
        "type": "36/72",
        "block": "HZ",
        "number": "1",
        "price": 200000000,
    }
    r = requests.post(f"{API}/developer/units", headers=_h(tokens["dev1"]), json=payload, timeout=30)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"


def test_dev1_cannot_modify_dev2_unit(tokens):
    dev2_projects = _dev_projects(tokens["dev2"])
    target = dev2_projects[0]
    u = requests.get(f"{API}/projects/{target['id']}", timeout=30).json().get("units", [])
    assert u, "dev2 project should have units"
    unit_id = u[0]["id"]
    r = requests.put(
        f"{API}/developer/units/{unit_id}",
        headers=_h(tokens["dev1"]),
        json={"price": 111},
        timeout=30,
    )
    assert r.status_code == 403, f"PUT expected 403, got {r.status_code}"
    r2 = requests.delete(f"{API}/developer/units/{unit_id}", headers=_h(tokens["dev1"]), timeout=30)
    assert r2.status_code == 403, f"DELETE expected 403, got {r2.status_code}"


# ---- SPR queue scoping ----
@pytest.mark.parametrize("dev_key", ["dev1", "dev2", "dev3"])
def test_spr_queue_scoped(tokens, dev_key):
    r = requests.get(f"{API}/developer/spr-queue", headers=_h(tokens[dev_key]), timeout=30)
    assert r.status_code == 200, r.text
    items = r.json()
    assert isinstance(items, list)
    # All items must reference projects owned by this developer
    owned_ids = {p["id"] for p in _dev_projects(tokens[dev_key])}
    for it in items:
        pid = it.get("project_id") or (it.get("project") or {}).get("id")
        if pid:
            assert pid in owned_ids, f"{dev_key} SPR queue leaked project {pid}"


# ---- Bank isolation ----
def test_btn_only_sees_btn_apps(tokens):
    r = requests.get(f"{API}/kpr/applications", headers=_h(tokens["btn"]), timeout=30)
    assert r.status_code == 200, r.text
    for a in r.json():
        assert a.get("bank") == "Bank BTN", f"leak: {a}"


def test_dki_only_sees_dki_apps(tokens):
    r = requests.get(f"{API}/kpr/applications", headers=_h(tokens["dki"]), timeout=30)
    assert r.status_code == 200, r.text
    for a in r.json():
        assert a.get("bank") == "Bank DKI", f"leak: {a}"


def test_admin_sees_all_kpr(tokens):
    r = requests.get(f"{API}/kpr/applications", headers=_h(tokens["admin"]), timeout=30)
    assert r.status_code == 200


# ---- Stats scoping (basic sanity) ----
def test_stats_scoped_by_role(tokens):
    for key in ["admin", "dev1", "dev2", "btn", "dki"]:
        r = requests.get(f"{API}/stats", headers=_h(tokens[key]), timeout=30)
        assert r.status_code == 200, f"{key} stats failed: {r.status_code} {r.text}"
