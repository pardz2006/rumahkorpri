"""Tests for new features: object storage, edit/delete unit, DP full payment."""
import os
import uuid
import base64
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

TINY_PNG = "data:image/png;base64," + base64.b64encode(
    bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000000000200015E5DFB7F0000000049454E44AE426082")
).decode()


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def dev_token():
    return _login("developer@rumahkorpri.com", "developer123")


@pytest.fixture(scope="module")
def consumer_token():
    return _login("consumer@rumahkorpri.com", "consumer123")


@pytest.fixture(scope="module")
def project_id(dev_token):
    r = requests.post(f"{API}/developer/projects", json={
        "name": f"TEST_NF_Proyek_{uuid.uuid4().hex[:6]}",
        "location": "NF Test City",
        "address_detail": "Jl. NF",
        "developer_name": "PT NF Dev",
        "description": "NF",
        "image": TINY_PNG,
        "program": "KOMERSIAL",
    }, headers=_h(dev_token), timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


class TestObjectStorage:
    def test_create_unit_returns_files_path_and_serves(self, dev_token, project_id):
        r = requests.post(f"{API}/developer/units", json={
            "project_id": project_id,
            "type": "TEST_NF_Tipe",
            "block": "N",
            "number": str(uuid.uuid4().int)[:4],
            "price": 300000000,
            "land_area": 60,
            "building_area": 30,
            "image_front": TINY_PNG,
            "image_layout": TINY_PNG,
            "image_siteplan": TINY_PNG,
        }, headers=_h(dev_token), timeout=20)
        assert r.status_code == 200, r.text
        u = r.json()
        assert u["image_front"].startswith("/api/files/"), f"Expected /api/files/ path, got: {u['image_front']}"
        assert u["image_layout"].startswith("/api/files/")
        assert u["image_siteplan"].startswith("/api/files/")
        pytest.unit_id = u["id"]
        pytest.image_front = u["image_front"]

        # GET served file
        served = requests.get(f"{BASE_URL}{u['image_front']}", timeout=15)
        assert served.status_code == 200, served.text
        assert served.headers.get("content-type", "").startswith("image/")
        assert len(served.content) > 0


class TestUpdateDeleteUnit:
    def test_update_price(self, dev_token):
        assert hasattr(pytest, "unit_id")
        new_price = 333000000
        r = requests.put(f"{API}/developer/units/{pytest.unit_id}",
                         json={"price": new_price}, headers=_h(dev_token), timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["price"] == new_price

    def test_consumer_cannot_update(self, consumer_token):
        r = requests.put(f"{API}/developer/units/{pytest.unit_id}",
                         json={"price": 100}, headers=_h(consumer_token), timeout=10)
        assert r.status_code == 403

    def test_consumer_cannot_delete(self, consumer_token):
        r = requests.delete(f"{API}/developer/units/{pytest.unit_id}",
                            headers=_h(consumer_token), timeout=10)
        assert r.status_code == 403

    def test_delete_available_unit(self, dev_token, project_id):
        # Create a second unit to delete
        r = requests.post(f"{API}/developer/units", json={
            "project_id": project_id,
            "type": "TEST_NF_Del",
            "block": "D",
            "number": str(uuid.uuid4().int)[:4],
            "price": 250000000,
            "land_area": 60,
            "building_area": 30,
        }, headers=_h(dev_token), timeout=15)
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        d = requests.delete(f"{API}/developer/units/{uid}", headers=_h(dev_token), timeout=10)
        assert d.status_code == 200
        # Ensure gone from project
        pd = requests.get(f"{API}/projects/{project_id}", timeout=10).json()
        assert not any(x["id"] == uid for x in pd["units"])


class TestFullDpPayment:
    """End-to-end: create booking, pay booking fee, developer approves, pay DP."""

    def test_full_dp_flow(self, dev_token, consumer_token, project_id):
        # Create unit
        r = requests.post(f"{API}/developer/units", json={
            "project_id": project_id,
            "type": "TEST_NF_DP",
            "block": "P",
            "number": str(uuid.uuid4().int)[:4],
            "price": 232000000,
            "land_area": 60,
            "building_area": 30,
        }, headers=_h(dev_token), timeout=15)
        assert r.status_code == 200
        unit_id = r.json()["id"]

        # Consumer creates booking
        r = requests.post(f"{API}/bookings", headers=_h(consumer_token), json={
            "unit_id": unit_id, "program": "FLPP", "dp_percent": 10,
            "tenor_years": 15, "payment_method": "VA_BTN"
        }, timeout=15)
        assert r.status_code == 200, r.text
        booking = r.json()
        bid = booking["id"]
        assert booking.get("dp_amount", 0) > 0, "dp_amount should be set at booking"
        assert booking.get("dp_payment_status") == "pending"
        dp_amount = booking["dp_amount"]

        # Pay booking fee (webhook)
        r = requests.post(f"{API}/payments/webhook", json={
            "booking_id": bid, "status": "paid"
        }, timeout=10)
        assert r.status_code == 200

        # Try to pay DP before SPR issued -> 400
        r = requests.post(f"{API}/bookings/{bid}/pay-dp", headers=_h(consumer_token), timeout=10)
        assert r.status_code == 400, f"Expected 400 before SPR issued, got {r.status_code}"

        # Developer approves SPR
        sig = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        r = requests.post(f"{API}/bookings/{bid}/spr/approve",
                          headers=_h(dev_token), json={"signature": sig}, timeout=30)
        assert r.status_code == 200, r.text

        # Initiate DP
        r = requests.post(f"{API}/bookings/{bid}/pay-dp", headers=_h(consumer_token), timeout=10)
        assert r.status_code == 200, r.text
        pay = r.json()
        assert pay["kind"] == "dp"
        assert pay["amount"] == dp_amount

        # Webhook confirm DP
        r = requests.post(f"{API}/payments/webhook", json={
            "booking_id": bid, "status": "paid", "kind": "dp"
        }, timeout=10)
        assert r.status_code == 200

        # Verify
        b = requests.get(f"{API}/bookings/{bid}", headers=_h(consumer_token), timeout=10).json()
        assert b["dp_payment_status"] == "paid"
        assert b.get("dp_ref")

        # Try to pay again -> 400
        r = requests.post(f"{API}/bookings/{bid}/pay-dp", headers=_h(consumer_token), timeout=10)
        assert r.status_code == 400


class TestDeleteBookedUnitBlocked:
    def test_cannot_delete_booked_unit(self, dev_token, consumer_token, project_id):
        # Create unit and book it
        r = requests.post(f"{API}/developer/units", json={
            "project_id": project_id,
            "type": "TEST_NF_Booked",
            "block": "B",
            "number": str(uuid.uuid4().int)[:4],
            "price": 200000000,
            "land_area": 60,
            "building_area": 30,
        }, headers=_h(dev_token), timeout=15)
        unit_id = r.json()["id"]
        rb = requests.post(f"{API}/bookings", headers=_h(consumer_token), json={
            "unit_id": unit_id, "program": "FLPP", "dp_percent": 10,
            "tenor_years": 15, "payment_method": "QRIS"
        }, timeout=15)
        assert rb.status_code == 200
        # Try delete -> 400
        d = requests.delete(f"{API}/developer/units/{unit_id}", headers=_h(dev_token), timeout=10)
        assert d.status_code == 400, f"Expected 400 for booked unit delete, got {d.status_code}"
