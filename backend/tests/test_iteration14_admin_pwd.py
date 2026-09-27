"""Iteration 14: Super Admin user management + change-password."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
    open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()
API = f"{BASE_URL}/api"


def login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    return r


def auth_h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def super_token():
    r = login("pardz2006@gmail.com", "korpri123")
    assert r.status_code == 200, r.text
    return r.json()["token"]


# ---------- superuser guard + list ----------
def test_non_super_cannot_list(super_token):
    admin = login("admin@rumahkorpri.com", "korpri123").json()["token"]
    r = requests.get(f"{API}/admin/users", headers=auth_h(admin))
    assert r.status_code == 403

def test_super_list_users(super_token):
    r = requests.get(f"{API}/admin/users", headers=auth_h(super_token))
    assert r.status_code == 200
    users = r.json()
    assert any(u.get("is_superuser") for u in users)
    assert any(u["email"] == "consumer@rumahkorpri.com" for u in users)


# ---------- CRUD ----------
@pytest.fixture(scope="module")
def created_user_id(super_token):
    email = f"TEST_iter14_{int(time.time())}@rumahkorpri.com".lower()
    r = requests.post(f"{API}/admin/users", headers=auth_h(super_token), json={
        "name": "TEST Dev", "email": email, "password": "test1234",
        "role": "admin_developer", "company": "TEST PT Iter14"
    })
    assert r.status_code == 200, r.text
    uid = r.json()["id"]
    yield uid, email
    requests.delete(f"{API}/admin/users/{uid}", headers=auth_h(super_token))


def test_create_appears_in_list(super_token, created_user_id):
    uid, email = created_user_id
    r = requests.get(f"{API}/admin/users", headers=auth_h(super_token))
    assert any(u["id"] == uid and u["email"] == email for u in r.json())


def test_edit_name(super_token, created_user_id):
    uid, _ = created_user_id
    r = requests.put(f"{API}/admin/users/{uid}", headers=auth_h(super_token),
                     json={"name": "TEST Dev Renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "TEST Dev Renamed"


def test_cannot_edit_superuser(super_token):
    users = requests.get(f"{API}/admin/users", headers=auth_h(super_token)).json()
    su = next(u for u in users if u.get("is_superuser"))
    r = requests.put(f"{API}/admin/users/{su['id']}", headers=auth_h(super_token),
                     json={"name": "hack"})
    assert r.status_code == 403


# ---------- disable/enable ----------
def test_disable_and_reenable_consumer(super_token):
    users = requests.get(f"{API}/admin/users", headers=auth_h(super_token)).json()
    c = next(u for u in users if u["email"] == "consumer2@rumahkorpri.com")
    try:
        r = requests.patch(f"{API}/admin/users/{c['id']}/status",
                           headers=auth_h(super_token), json={"disabled": True})
        assert r.status_code == 200
        # blocked login
        lr = login("consumer2@rumahkorpri.com", "consumer123")
        assert lr.status_code == 403
        assert "dinonaktifkan" in lr.text
    finally:
        r = requests.patch(f"{API}/admin/users/{c['id']}/status",
                           headers=auth_h(super_token), json={"disabled": False})
        assert r.status_code == 200
    lr = login("consumer2@rumahkorpri.com", "consumer123")
    assert lr.status_code == 200


# ---------- visibility (hide developer) ----------
def test_hide_developer_filters_projects(super_token):
    users = requests.get(f"{API}/admin/users", headers=auth_h(super_token)).json()
    dev = next(u for u in users if u["email"] == "developer@rumahkorpri.com")
    baseline = len(requests.get(f"{API}/projects").json())
    # sample a project of this dev
    proj = next((p for p in requests.get(f"{API}/projects").json()
                 if p.get("developer_id") == dev["id"]), None)
    assert proj, "developer has no project"
    try:
        r = requests.patch(f"{API}/admin/users/{dev['id']}/visibility",
                           headers=auth_h(super_token), json={"hidden": True})
        assert r.status_code == 200
        after = requests.get(f"{API}/projects").json()
        assert len(after) < baseline
        assert not any(p.get("developer_id") == dev["id"] for p in after)
        # detail 404
        d = requests.get(f"{API}/projects/{proj['id']}")
        assert d.status_code == 404
    finally:
        requests.patch(f"{API}/admin/users/{dev['id']}/visibility",
                       headers=auth_h(super_token), json={"hidden": False})
    restored = requests.get(f"{API}/projects").json()
    assert len(restored) == baseline


def test_cannot_hide_consumer(super_token):
    users = requests.get(f"{API}/admin/users", headers=auth_h(super_token)).json()
    c = next(u for u in users if u["email"] == "consumer@rumahkorpri.com")
    r = requests.patch(f"{API}/admin/users/{c['id']}/visibility",
                       headers=auth_h(super_token), json={"hidden": True})
    assert r.status_code == 400


# ---------- change-password ----------
def test_change_password_flow():
    # use consumer3 to isolate
    email, orig = "consumer3@rumahkorpri.com", "consumer123"
    tok = login(email, orig).json()["token"]
    # wrong current
    r = requests.post(f"{API}/auth/change-password", headers=auth_h(tok),
                      json={"current_password": "wrong123", "new_password": "newpass123"})
    assert r.status_code in (400, 401, 403)
    # still original works
    assert login(email, orig).status_code == 200
    # correct
    r = requests.post(f"{API}/auth/change-password", headers=auth_h(tok),
                      json={"current_password": orig, "new_password": "newpass123"})
    assert r.status_code == 200
    assert login(email, orig).status_code != 200
    assert login(email, "newpass123").status_code == 200
    # revert
    tok2 = login(email, "newpass123").json()["token"]
    r = requests.post(f"{API}/auth/change-password", headers=auth_h(tok2),
                      json={"current_password": "newpass123", "new_password": orig})
    assert r.status_code == 200
    assert login(email, orig).status_code == 200
