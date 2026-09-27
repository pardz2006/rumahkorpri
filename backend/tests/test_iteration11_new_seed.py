"""Iteration 11 — Verify new seed users (bankdki2/3, developer4/5/6), isolation, and additive catalog growth."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://rumah-deps.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    return data["token"], data["user"]


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- New logins ----------
NEW_USERS = [
    ("bankdki2@rumahkorpri.com", "dki123", "btn_evaluator", "Bank DKI"),
    ("bankdki3@rumahkorpri.com", "dki123", "btn_evaluator", "Bank DKI"),
    ("developer4@rumahkorpri.com", "developer123", "admin_developer", "PT Cendana Propertindo"),
    ("developer5@rumahkorpri.com", "developer123", "admin_developer", "PT Harmoni Land Indonesia"),
    ("developer6@rumahkorpri.com", "developer123", "admin_developer", "PT Sinar Purnama Development"),
]


@pytest.mark.parametrize("email,pwd,role,company_or_bank", NEW_USERS)
def test_new_logins(email, pwd, role, company_or_bank):
    tok, user = _login(email, pwd)
    assert user.get("role") == role, f"{email} role={user.get('role')}"
    if role == "btn_evaluator":
        assert user.get("bank") == company_or_bank, f"{email} bank={user.get('bank')}"
    else:
        # developer users should belong to the given company
        company = user.get("company") or user.get("developer_company") or user.get("developer_name")
        assert company_or_bank in str(user), f"{email} user payload missing company: {user}"


# ---------- Developer isolation ----------
DEV_EXPECTED = {
    "developer4@rumahkorpri.com": {"Cendana Asri Residence", "Cendana Riverpark"},
    "developer5@rumahkorpri.com": {"Harmoni Land Semarang", "Harmoni Waterfront City"},
    "developer6@rumahkorpri.com": {"Purnama Green Valley", "Purnama Sky Residence"},
}


@pytest.mark.parametrize("email,expected", list(DEV_EXPECTED.items()))
def test_new_developer_projects_isolation(email, expected):
    tok, _ = _login(email, "developer123")
    r = requests.get(f"{API}/developer/projects", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, r.text
    names = {p["name"] for p in r.json()}
    assert names == expected, f"{email}: got {names}, expected {expected}"


def test_original_devs_unchanged():
    for email in ["developer@rumahkorpri.com", "developer2@rumahkorpri.com", "developer3@rumahkorpri.com"]:
        tok, _ = _login(email, "developer123")
        r = requests.get(f"{API}/developer/projects", headers=_hdr(tok), timeout=30)
        assert r.status_code == 200
        assert len(r.json()) == 2, f"{email} project count={len(r.json())}"


def test_cross_developer_mutation_403():
    # developer4 tries to update a project belonging to developer5
    tok4, _ = _login("developer4@rumahkorpri.com", "developer123")
    tok5, _ = _login("developer5@rumahkorpri.com", "developer123")
    r5 = requests.get(f"{API}/developer/projects", headers=_hdr(tok5), timeout=30)
    proj5 = r5.json()[0]
    pid = proj5["id"]
    # Try PUT
    r = requests.put(f"{API}/developer/projects/{pid}", headers=_hdr(tok4),
                     json={"name": proj5["name"], "description": "hack"}, timeout=30)
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
    # Try adding unit (project belongs to dev5, dev4 attempts)
    r_u = requests.post(f"{API}/developer/units", headers=_hdr(tok4),
                        json={"project_id": pid, "type": "36", "block": "Z", "number": "999",
                              "price": 200000000, "stock": 1}, timeout=30)
    assert r_u.status_code == 403, f"expected 403 on unit create, got {r_u.status_code}: {r_u.text}"


# ---------- Bank DKI new evaluators ----------
def test_bankdki_evaluators_see_only_dki():
    for email in ["bankdki2@rumahkorpri.com", "bankdki3@rumahkorpri.com", "bankdki@rumahkorpri.com"]:
        tok, _ = _login(email, "dki123")
        r = requests.get(f"{API}/kpr/applications", headers=_hdr(tok), timeout=30)
        assert r.status_code == 200, r.text
        apps = r.json()
        for a in apps:
            assert a.get("bank") == "Bank DKI", f"{email} saw non-DKI app: {a}"


def test_btn_evaluator_sees_only_btn():
    tok, _ = _login("btn@rumahkorpri.com", "btn123")
    r = requests.get(f"{API}/kpr/applications", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200
    for a in r.json():
        assert a.get("bank") == "Bank BTN"


def test_cross_bank_patch_403():
    # bankdki2 tries to patch a BTN application
    tok_btn, _ = _login("btn@rumahkorpri.com", "btn123")
    btn_apps = requests.get(f"{API}/kpr/applications", headers=_hdr(tok_btn), timeout=30).json()
    if not btn_apps:
        pytest.skip("no BTN application to test cross-bank patch")
    app_id = btn_apps[0]["id"]
    tok_dki, _ = _login("bankdki2@rumahkorpri.com", "dki123")
    r = requests.patch(f"{API}/kpr/applications/{app_id}", headers=_hdr(tok_dki),
                       json={"status": "pre_approved"}, timeout=30)
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


# ---------- Catalog additive growth ----------
def test_catalog_12_projects_49_units():
    r = requests.get(f"{API}/projects", timeout=30)
    assert r.status_code == 200
    projects = r.json()
    assert len(projects) == 12, f"expected 12 projects, got {len(projects)}: {[p['name'] for p in projects]}"
    total_units = 0
    for p in projects:
        units = p.get("units") or []
        total_units += len(units)
    assert total_units == 49, f"expected 49 units, got {total_units}"


def test_existing_kpr_apps_persist():
    # iteration_10 created 1 BTN pre_approved + 1 DKI pending
    tok_btn, _ = _login("btn@rumahkorpri.com", "btn123")
    btn_apps = requests.get(f"{API}/kpr/applications", headers=_hdr(tok_btn), timeout=30).json()
    tok_dki, _ = _login("bankdki@rumahkorpri.com", "dki123")
    dki_apps = requests.get(f"{API}/kpr/applications", headers=_hdr(tok_dki), timeout=30).json()
    assert len(btn_apps) >= 1, f"BTN apps missing: {btn_apps}"
    assert len(dki_apps) >= 1, f"DKI apps missing: {dki_apps}"
    # There should be at least one pre_approved BTN
    assert any(a.get("status") == "pre_approved" for a in btn_apps), f"no pre_approved BTN found: {btn_apps}"
