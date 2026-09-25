"""Iteration 10: admin_korpri new login + full booking->pay->SPR->bank isolation flow."""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://rumah-deps.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code}: {r.text}"
    j = r.json()
    return j["token"], j["user"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


# ---------- ADMIN LOGIN (new pardz) ----------
def test_new_admin_korpri_login_pardz():
    tok, user = _login("pardz2006@gmail.com", "korpri123")
    assert user["role"] == "admin_korpri", user
    # Sanity: token authorised for admin-scoped route
    r = requests.get(f"{API}/kpr/applications", headers=_h(tok), timeout=30)
    assert r.status_code == 200


def test_owner_admin_still_works():
    tok, user = _login("admin@rumahkorpri.com", "korpri123")
    assert user["role"] == "admin_korpri"


# ---------- FULL FLOW: two bookings, two banks ----------
@pytest.fixture(scope="module")
def flow():
    admin_tok, _ = _login("admin@rumahkorpri.com", "korpri123")
    consumer_tok, consumer_user = _login("consumer@rumahkorpri.com", "consumer123")
    dev_tok, _ = _login("developer@rumahkorpri.com", "developer123")
    btn_tok, _ = _login("btn@rumahkorpri.com", "btn123")
    dki_tok, _ = _login("bankdki@rumahkorpri.com", "dki123")

    projects = requests.get(f"{API}/projects", timeout=30).json()
    btn_proj = next(p for p in projects if p["name"] == "Griya KORPRI Harmoni")
    dki_proj = next(p for p in projects if p["name"] == "Bumi ASN Residence")
    assert btn_proj.get("bank") == "Bank BTN"
    assert dki_proj.get("bank") == "Bank DKI"

    def _first_available(proj):
        for u in proj.get("units", []):
            if u.get("status") == "available":
                return u
        return None

    btn_unit = _first_available(btn_proj)
    dki_unit = _first_available(dki_proj)
    assert btn_unit, "no available unit in BTN project"
    assert dki_unit, "no available unit in DKI project"

    def _create_booking(unit, program):
        r = requests.post(
            f"{API}/bookings",
            headers=_h(consumer_tok),
            json={"unit_id": unit["id"], "program": program, "dp_percent": 10,
                  "tenor_years": 15, "payment_method": "QRIS"},
            timeout=30,
        )
        assert r.status_code == 200, f"create booking failed: {r.status_code} {r.text}"
        return r.json()

    btn_booking = _create_booking(btn_unit, "FLPP")
    dki_booking = _create_booking(dki_unit, "KOMERSIAL")

    btn_id = btn_booking.get("id") or btn_booking.get("_id")
    dki_id = dki_booking.get("id") or dki_booking.get("_id")
    assert btn_id and dki_id, (btn_booking, dki_booking)

    # initiate payment (booking fee)
    for bid in (btn_id, dki_id):
        r = requests.post(f"{API}/bookings/{bid}/pay", headers=_h(consumer_tok), timeout=30)
        assert r.status_code == 200, f"init pay {bid}: {r.status_code} {r.text}"

    # webhook -> paid
    for bid in (btn_id, dki_id):
        r = requests.post(
            f"{API}/payments/webhook",
            json={"booking_id": bid, "status": "paid", "kind": "booking_fee"},
            timeout=30,
        )
        assert r.status_code == 200, f"webhook {bid}: {r.status_code} {r.text}"

    # developer approves SPR (dev1 owns both)
    sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    for bid in (btn_id, dki_id):
        r = requests.post(
            f"{API}/bookings/{bid}/spr/approve",
            headers=_h(dev_tok),
            json={"signature": sig},
            timeout=60,
        )
        assert r.status_code == 200, f"spr approve {bid}: {r.status_code} {r.text}"

    return {
        "admin": admin_tok, "consumer": consumer_tok, "dev": dev_tok,
        "btn": btn_tok, "dki": dki_tok,
        "btn_booking_id": btn_id, "dki_booking_id": dki_id,
        "btn_project_id": btn_proj["id"], "dki_project_id": dki_proj["id"],
    }


def test_btn_evaluator_sees_only_btn_app(flow):
    r = requests.get(f"{API}/kpr/applications", headers=_h(flow["btn"]), timeout=30)
    assert r.status_code == 200
    apps = r.json()
    assert len(apps) >= 1
    for a in apps:
        assert a.get("bank") == "Bank BTN", a
    # must contain the btn booking, must NOT contain the dki booking
    booking_ids = {a["booking_id"] for a in apps}
    assert flow["btn_booking_id"] in booking_ids
    assert flow["dki_booking_id"] not in booking_ids


def test_dki_evaluator_sees_only_dki_app(flow):
    r = requests.get(f"{API}/kpr/applications", headers=_h(flow["dki"]), timeout=30)
    assert r.status_code == 200
    apps = r.json()
    assert len(apps) >= 1
    for a in apps:
        assert a.get("bank") == "Bank DKI", a
    booking_ids = {a["booking_id"] for a in apps}
    assert flow["dki_booking_id"] in booking_ids
    assert flow["btn_booking_id"] not in booking_ids


def test_cross_bank_patch_returns_403(flow):
    # BTN evaluator PATCHing a DKI application must be 403
    r = requests.get(f"{API}/kpr/applications", headers=_h(flow["dki"]), timeout=30)
    dki_app_id = next(a["id"] for a in r.json() if a["booking_id"] == flow["dki_booking_id"])
    r2 = requests.patch(
        f"{API}/kpr/applications/{dki_app_id}",
        headers=_h(flow["btn"]),
        json={"status": "pre_approved", "evaluator_note": "cross-bank hack"},
        timeout=30,
    )
    assert r2.status_code == 403, f"expected 403, got {r2.status_code}: {r2.text}"


def test_same_bank_patch_succeeds(flow):
    r = requests.get(f"{API}/kpr/applications", headers=_h(flow["btn"]), timeout=30)
    btn_app_id = next(a["id"] for a in r.json() if a["booking_id"] == flow["btn_booking_id"])
    r2 = requests.patch(
        f"{API}/kpr/applications/{btn_app_id}",
        headers=_h(flow["btn"]),
        json={"status": "pre_approved", "evaluator_note": "ok"},
        timeout=30,
    )
    assert r2.status_code == 200, f"same-bank patch: {r2.status_code} {r2.text}"
    # verify persisted
    r3 = requests.get(f"{API}/kpr/applications", headers=_h(flow["btn"]), timeout=30)
    updated = next(a for a in r3.json() if a["id"] == btn_app_id)
    assert updated["status"] == "pre_approved"


# ---------- REGRESSION: developer isolation ----------
def test_developer_still_scoped_to_2_projects():
    dev_tok, _ = _login("developer@rumahkorpri.com", "developer123")
    r = requests.get(f"{API}/developer/projects", headers=_h(dev_tok), timeout=30)
    assert r.status_code == 200
    names = {p["name"] for p in r.json()}
    assert names == {"Griya KORPRI Harmoni", "Bumi ASN Residence"}, names
