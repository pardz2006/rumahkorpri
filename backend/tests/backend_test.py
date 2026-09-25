"""End-to-end backend tests for Sistem Pemesanan Rumah & CRM Rumah KORPRI."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://korpri-housing-crm.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "admin_korpri": ("pardz2006@gmail.com", "korpri123"),
    "admin_developer": ("developer@rumahkorpri.com", "developer123"),
    "btn_evaluator": ("btn@rumahkorpri.com", "btn123"),
    "consumer": ("consumer@rumahkorpri.com", "consumer123"),
}

# Shared state across tests
STATE = {}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Auth ----------
class TestAuth:
    def test_login_all_roles(self):
        for role, (email, pwd) in CREDS.items():
            token = _login(email, pwd)
            STATE[f"token_{role}"] = token
            me = requests.get(f"{API}/auth/me", headers=_h(token), timeout=10)
            assert me.status_code == 200
            assert me.json()["role"] == role

    def test_register_new_consumer(self):
        email = f"TEST_user_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/auth/register", json={
            "name": "Test Consumer", "email": email, "password": "test123",
            "phone": "081200000000",
        }, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["role"] == "consumer"
        assert data["user"]["email"] == email.lower()

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": "x@x.com", "password": "wrong"}, timeout=10)
        assert r.status_code == 401


# ---------- Public ----------
class TestPublic:
    def test_list_projects(self):
        r = requests.get(f"{API}/projects", timeout=10)
        assert r.status_code == 200
        projects = r.json()
        assert len(projects) >= 1
        STATE["projects"] = projects
        # Find an available unit
        for p in projects:
            for u in p["units"]:
                if u["status"] == "available":
                    STATE["unit"] = u
                    STATE["project"] = p
                    return
        pytest.fail("No available unit for booking test")

    def test_kpr_simulate(self):
        r = requests.post(f"{API}/kpr/simulate", json={
            "price": 168000000, "dp_percent": 10, "tenor_years": 15, "program": "FLPP"
        }, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "loan_amount" in data
        assert data["loan_amount"] > 0
        # Should have installment info
        keys = list(data.keys())
        assert any("install" in k.lower() or "cicilan" in k.lower() or "monthly" in k.lower() for k in keys), keys


# ---------- Full flow: booking -> pay -> SPR -> KPR ----------
class TestBookingFlow:
    def test_00_setup_tokens_and_unit(self):
        for role, (email, pwd) in CREDS.items():
            STATE[f"token_{role}"] = _login(email, pwd)
        projects = requests.get(f"{API}/projects", timeout=10).json()
        for p in projects:
            for u in p["units"]:
                if u["status"] == "available":
                    STATE["unit"] = u
                    STATE["project"] = p
                    return
        pytest.fail("No available unit")

    def test_01_consumer_creates_booking(self):
        token = STATE["token_consumer"]
        unit = STATE["unit"]
        r = requests.post(f"{API}/bookings", headers=_h(token), json={
            "unit_id": unit["id"], "program": "FLPP", "dp_percent": 10, "tenor_years": 15,
            "payment_method": "VA_BTN"
        }, timeout=15)
        assert r.status_code == 200, r.text
        booking = r.json()
        assert booking["payment_status"] == "pending"
        assert booking["va_number"]
        STATE["booking_id"] = booking["id"]

        # Verify unit became booked
        pr = requests.get(f"{API}/projects/{STATE['project']['id']}", timeout=10)
        units = pr.json()["units"]
        u = next(x for x in units if x["id"] == unit["id"])
        assert u["status"] == "booked"

    def test_02_role_forbidden_admin_endpoint(self):
        token = STATE["token_consumer"]
        r = requests.get(f"{API}/stats", headers=_h(token), timeout=10)
        assert r.status_code == 403

    def test_03_initiate_payment(self):
        token = STATE["token_consumer"]
        r = requests.post(f"{API}/bookings/{STATE['booking_id']}/pay", headers=_h(token), timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["amount"] == 5000000
        assert data["va_number"]

    def test_04_payment_webhook_marks_paid(self):
        r = requests.post(f"{API}/payments/webhook", json={
            "booking_id": STATE["booking_id"], "status": "paid"
        }, timeout=10)
        assert r.status_code == 200
        assert r.json()["ok"] is True
        # Verify booking status
        token = STATE["token_consumer"]
        b = requests.get(f"{API}/bookings/{STATE['booking_id']}", headers=_h(token), timeout=10).json()
        assert b["payment_status"] == "paid"
        assert b["spr_status"] == "draft"
        assert b["spr_number"]

    def test_05_developer_spr_queue(self):
        token = STATE["token_admin_developer"]
        r = requests.get(f"{API}/developer/spr-queue", headers=_h(token), timeout=10)
        assert r.status_code == 200
        queue = r.json()
        assert any(b["id"] == STATE["booking_id"] for b in queue)

    def test_06_developer_approves_spr(self):
        token = STATE["token_admin_developer"]
        sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        r = requests.post(f"{API}/bookings/{STATE['booking_id']}/spr/approve",
                          headers=_h(token), json={"signature": sig}, timeout=30)
        assert r.status_code == 200, r.text
        b = r.json()
        assert b["spr_status"] == "issued"

    def test_07_spr_pdf_downloadable(self):
        r = requests.get(f"{API}/bookings/{STATE['booking_id']}/spr.pdf", timeout=15)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_08_unit_marked_sold(self):
        pr = requests.get(f"{API}/projects/{STATE['project']['id']}", timeout=10)
        units = pr.json()["units"]
        u = next(x for x in units if x["id"] == STATE["unit"]["id"])
        assert u["status"] == "sold"

    def test_09_kpr_application_created(self):
        token = STATE["token_btn_evaluator"]
        r = requests.get(f"{API}/kpr/applications", headers=_h(token), timeout=10)
        assert r.status_code == 200
        apps = r.json()
        matches = [a for a in apps if a["booking_id"] == STATE["booking_id"]]
        assert matches, "KPR application not auto-created"
        STATE["kpr_app_id"] = matches[0]["id"]
        assert matches[0]["status"] == "pending"

    def test_10_consumer_uploads_document(self):
        token = STATE["token_consumer"]
        r = requests.post(f"{API}/bookings/{STATE['booking_id']}/documents",
                          headers=_h(token),
                          json={"doc_type": "KTP",
                                "file_data": "data:image/png;base64,iVBORw0KGgo=",
                                "file_name": "ktp.png"}, timeout=10)
        assert r.status_code == 200
        # Verify
        b = requests.get(f"{API}/bookings/{STATE['booking_id']}", headers=_h(token), timeout=10).json()
        docs = {d["doc_type"]: d for d in b["documents"]}
        assert "KTP" in docs and docs["KTP"]["status"] == "uploaded"
        # Save a missing doc id for verify test
        STATE["ktp_doc_id"] = docs["KTP"]["id"]

    def test_11_admin_verifies_document(self):
        token = STATE["token_admin_korpri"]
        r = requests.patch(f"{API}/documents/{STATE['ktp_doc_id']}/verify",
                           headers=_h(token),
                           json={"status": "valid", "note": "OK"}, timeout=10)
        assert r.status_code == 200

    def test_12_admin_sends_followup(self):
        token = STATE["token_admin_korpri"]
        r = requests.post(f"{API}/bookings/{STATE['booking_id']}/followup",
                          headers=_h(token), timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert len(data["missing"]) >= 1

    def test_13_wa_logs_viewable(self):
        token = STATE["token_admin_korpri"]
        r = requests.get(f"{API}/wa-logs", headers=_h(token), timeout=10)
        assert r.status_code == 200
        logs = r.json()
        assert any(w.get("booking_id") == STATE["booking_id"] for w in logs)

    def test_14_btn_updates_kpr_status(self):
        token = STATE["token_btn_evaluator"]
        r = requests.patch(f"{API}/kpr/applications/{STATE['kpr_app_id']}",
                           headers=_h(token),
                           json={"status": "pre_approved",
                                 "evaluator_note": "Layak lanjut",
                                 "slik_note": "Kol 1"}, timeout=10)
        assert r.status_code == 200

    def test_15_notifications_for_consumer(self):
        token = STATE["token_consumer"]
        r = requests.get(f"{API}/notifications", headers=_h(token), timeout=10)
        assert r.status_code == 200
        notifs = r.json()
        assert len(notifs) >= 1

    def test_16_consumer_cannot_view_others_booking(self):
        # Register new consumer, try to view first consumer's booking
        email = f"TEST_other_{uuid.uuid4().hex[:8]}@example.com"
        reg = requests.post(f"{API}/auth/register", json={
            "name": "Other", "email": email, "password": "x1234567"
        }, timeout=10)
        other_token = reg.json()["token"]
        r = requests.get(f"{API}/bookings/{STATE['booking_id']}", headers=_h(other_token), timeout=10)
        assert r.status_code == 403

    def test_17_stats(self):
        token = STATE["token_admin_korpri"]
        r = requests.get(f"{API}/stats", headers=_h(token), timeout=10)
        assert r.status_code == 200
        s = r.json()
        for k in ["total_bookings", "paid_bookings", "spr_issued",
                  "units_available", "units_sold", "kpr_pending", "kpr_approved",
                  "docs_missing"]:
            assert k in s
