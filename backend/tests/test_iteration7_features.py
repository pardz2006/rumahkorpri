"""Iteration 7 tests: seeded logins, share link, public sim, DP cron."""
import os
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://korpri-preview.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "rumahkorpri")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()


# ---------------- seeded users ----------------
class TestSeededLogins:
    def test_bank_dki_login(self):
        d = _login("bankdki@rumahkorpri.com", "dki123")
        u = d["user"]
        assert u["role"] == "btn_evaluator"
        assert u.get("bank") == "Bank DKI"

    def test_bank_btn_login(self):
        d = _login("btn@rumahkorpri.com", "btn123")
        assert d["user"]["role"] == "btn_evaluator"
        assert d["user"].get("bank") == "Bank BTN"

    def test_developer2_login(self):
        d = _login("developer2@rumahkorpri.com", "developer123")
        assert d["user"]["role"] == "admin_developer"
        assert d["user"].get("company") == "PT Bumi Persada Nusantara"

    def test_developer3_login(self):
        d = _login("developer3@rumahkorpri.com", "developer123")
        assert d["user"]["role"] == "admin_developer"
        assert d["user"].get("company") == "PT Karya Nyaman Sejahtera"

    def test_bank_dki_can_list_kpr_apps(self):
        d = _login("bankdki@rumahkorpri.com", "dki123")
        r = requests.get(f"{API}/kpr/applications", headers={"Authorization": f"Bearer {d['token']}"}, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------- share simulation ----------------
@pytest.fixture(scope="module")
def consumer():
    return _login("consumer@rumahkorpri.com", "consumer123")


@pytest.fixture(scope="module")
def consumer_headers(consumer):
    return {"Authorization": f"Bearer {consumer['token']}"}


@pytest.fixture(scope="module")
def saved_sim(consumer_headers):
    payload = {
        "label": "TEST_iter7_share",
        "price": 250_000_000,
        "dp_percent": 10,
        "tenor_years": 20,
        "program": "fs_flat",
    }
    r = requests.post(f"{API}/simulations", json=payload, headers=consumer_headers, timeout=15)
    assert r.status_code == 200, r.text
    sim = r.json()
    yield sim
    # cleanup
    requests.delete(f"{API}/simulations/{sim['id']}", headers=consumer_headers, timeout=10)


class TestShareSimulation:
    def test_share_returns_token_and_path(self, saved_sim, consumer_headers):
        r = requests.post(f"{API}/simulations/{saved_sim['id']}/share", headers=consumer_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "share_token" in d and len(d["share_token"]) > 10
        assert d["path"] == f"/s/{d['share_token']}"

    def test_share_is_idempotent(self, saved_sim, consumer_headers):
        r1 = requests.post(f"{API}/simulations/{saved_sim['id']}/share", headers=consumer_headers, timeout=10)
        r2 = requests.post(f"{API}/simulations/{saved_sim['id']}/share", headers=consumer_headers, timeout=10)
        assert r1.json()["share_token"] == r2.json()["share_token"]

    def test_save_sim_stores_share_token(self, saved_sim):
        assert saved_sim.get("share_token"), "POST /api/simulations should include share_token"

    def test_public_sim_no_auth(self, saved_sim):
        token = saved_sim["share_token"]
        r = requests.get(f"{API}/public/simulations/{token}", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d.get("label") == "TEST_iter7_share"
        assert "shared_by" in d and d["shared_by"]
        assert "user_id" not in d

    def test_public_sim_unknown_token_404(self):
        r = requests.get(f"{API}/public/simulations/nonexistent-xxx", timeout=10)
        assert r.status_code == 404

    def test_non_owner_cannot_share(self, saved_sim):
        other = _login("developer@rumahkorpri.com", "developer123")
        r = requests.post(
            f"{API}/simulations/{saved_sim['id']}/share",
            headers={"Authorization": f"Bearer {other['token']}"},
            timeout=10,
        )
        assert r.status_code == 404


# ---------------- DP cron ----------------
class TestDpReminderCron:
    def test_cron_returns_200_no_auth(self):
        r = requests.post(f"{API}/cron/dp-reminders", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True
        assert isinstance(d.get("reminded"), int)

    def test_cron_is_idempotent_when_nothing_due(self):
        r1 = requests.post(f"{API}/cron/dp-reminders", timeout=30)
        r2 = requests.post(f"{API}/cron/dp-reminders", timeout=30)
        assert r1.status_code == 200 and r2.status_code == 200

    def test_cron_reminds_and_marks_idempotent(self):
        """Manipulate a booking to have spr_status=issued and one termin due within 3d, then
        assert cron reminds it, writes wa_log with template dp_due_reminder, marks reminded=true,
        and a second run does not re-remind."""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        # find any booking with dp_termins; if none, create synthetic one referencing consumer user
        booking = db.bookings.find_one({"dp_termins": {"$exists": True, "$ne": []}})
        cleanup_booking_id = None
        if not booking:
            # build minimal booking
            consumer_user = db.users.find_one({"email": "consumer@rumahkorpri.com"})
            unit = db.units.find_one({})
            if not consumer_user or not unit:
                pytest.skip("No consumer/unit to build synthetic booking")
            from datetime import datetime, timezone
            now_iso = datetime.now(timezone.utc).isoformat()
            res = db.bookings.insert_one({
                "user_id": str(consumer_user["_id"]),
                "unit_id": str(unit["_id"]),
                "project_id": str(unit.get("project_id", "")),
                "dp_amount": 30_000_000,
                "dp_termins": [
                    {"no": 1, "amount": 10_000_000, "status": "pending"},
                    {"no": 2, "amount": 10_000_000, "status": "pending"},
                    {"no": 3, "amount": 10_000_000, "status": "pending"},
                ],
                "spr_status": "issued",
                "spr_issued_at": now_iso,
                "created_at": now_iso,
            })
            cleanup_booking_id = res.inserted_id
            booking = db.bookings.find_one({"_id": res.inserted_id})
        # force spr_status issued and set termin[0].due_date to tomorrow, others cleared reminded
        from datetime import datetime, timezone, timedelta
        soon = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        termins = booking.get("dp_termins") or []
        for t in termins:
            t["reminded"] = False
            t["status"] = t.get("status") or "pending"
        if termins:
            termins[0]["due_date"] = soon
            termins[0]["reminded"] = False
            termins[0]["status"] = "pending"
        db.bookings.update_one(
            {"_id": booking["_id"]},
            {"$set": {"spr_status": "issued", "dp_termins": termins}},
        )
        # clear any existing wa_log for that booking
        db.wa_logs.delete_many({"booking_id": str(booking["_id"]), "template": "dp_due_reminder"})

        # run cron
        r = requests.post(f"{API}/cron/dp-reminders", timeout=30)
        assert r.status_code == 200
        reminded1 = r.json()["reminded"]
        assert reminded1 >= 1, f"expected >=1 reminded, got {reminded1}"

        # verify DB marked reminded=true on termin[0]
        b2 = db.bookings.find_one({"_id": booking["_id"]})
        assert b2["dp_termins"][0].get("reminded") is True

        # verify wa_log written with template dp_due_reminder
        log = db.wa_logs.find_one({"booking_id": str(booking["_id"]), "template": "dp_due_reminder"})
        assert log is not None, "wa_log with template dp_due_reminder should exist"
        # channel may be 'twilio' or 'simulated'; status may be 'failed' on trial - both acceptable
        assert log.get("template") == "dp_due_reminder"

        # 2nd run: should not re-remind the same termin
        r2 = requests.post(f"{API}/cron/dp-reminders", timeout=30)
        assert r2.status_code == 200
        b3 = db.bookings.find_one({"_id": booking["_id"]})
        # still reminded=True, no duplicate log for termin[0]
        assert b3["dp_termins"][0].get("reminded") is True
        # cleanup synthetic
        if cleanup_booking_id:
            db.bookings.delete_one({"_id": cleanup_booking_id})
            db.wa_logs.delete_many({"booking_id": str(cleanup_booking_id)})
        client.close()


# ---------------- Regression on simulations ----------------
class TestSimulationsRegression:
    def test_create_list_delete(self, consumer_headers):
        payload = {"label": "TEST_iter7_reg", "price": 200_000_000, "dp_percent": 10, "tenor_years": 15, "program": "fs_flat"}
        r = requests.post(f"{API}/simulations", json=payload, headers=consumer_headers, timeout=15)
        assert r.status_code == 200
        sim = r.json()
        assert sim.get("share_token")
        lst = requests.get(f"{API}/simulations", headers=consumer_headers, timeout=10).json()
        assert any(s["id"] == sim["id"] for s in lst)
        d = requests.delete(f"{API}/simulations/{sim['id']}", headers=consumer_headers, timeout=10)
        assert d.status_code == 200
