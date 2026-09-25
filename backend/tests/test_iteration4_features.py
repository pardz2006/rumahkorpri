"""Iteration 4: photo magic-bytes validation, DP termin order enforcement, edit project."""
import os
import uuid
import base64
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

# Real 1x1 PNG bytes
PNG_BYTES = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000D49444154789C6360000000000200015E5DFB7F0000000049454E44AE426082"
)
TINY_PNG = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode()
# Text pretending to be image/png (fake magic bytes)
FAKE_IMG = "data:image/png;base64," + base64.b64encode(b"hello this is definitely not a real png file at all").decode()


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
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


# --------- Photo magic-bytes validation ---------
class TestPhotoValidation:
    def test_create_project_with_fake_image_rejected_400(self, dev_token):
        r = requests.post(f"{API}/developer/projects", json={
            "name": f"TEST_I4_Fake_{uuid.uuid4().hex[:6]}",
            "location": "X",
            "address_detail": "X",
            "description": "x",
            "image": FAKE_IMG,
            "program": "KOMERSIAL",
        }, headers=_h(dev_token), timeout=15)
        assert r.status_code == 400, r.text
        assert "gambar" in r.text.lower() or "image" in r.text.lower()

    def test_create_project_with_real_png_ok(self, dev_token):
        r = requests.post(f"{API}/developer/projects", json={
            "name": f"TEST_I4_Real_{uuid.uuid4().hex[:6]}",
            "location": "X",
            "address_detail": "X",
            "description": "x",
            "image": TINY_PNG,
            "program": "KOMERSIAL",
        }, headers=_h(dev_token), timeout=20)
        assert r.status_code == 200, r.text
        pytest.i4_project_id = r.json()["id"]
        assert r.json()["image"].startswith("/api/files/")

    def test_create_unit_with_fake_image_rejected_400(self, dev_token):
        assert hasattr(pytest, "i4_project_id")
        r = requests.post(f"{API}/developer/units", json={
            "project_id": pytest.i4_project_id,
            "type": "TEST_I4",
            "block": "Z", "number": str(uuid.uuid4().int)[:4],
            "price": 250000000, "land_area": 60, "building_area": 30,
            "image_front": FAKE_IMG,
        }, headers=_h(dev_token), timeout=15)
        assert r.status_code == 400, r.text


# --------- Edit project ---------
class TestEditProject:
    def test_edit_project_name_updates_units(self, dev_token):
        assert hasattr(pytest, "i4_project_id")
        pid = pytest.i4_project_id
        # Create a unit under this project first
        r = requests.post(f"{API}/developer/units", json={
            "project_id": pid,
            "type": "TEST_I4_U", "block": "E",
            "number": str(uuid.uuid4().int)[:4],
            "price": 200000000, "land_area": 60, "building_area": 30,
        }, headers=_h(dev_token), timeout=15)
        assert r.status_code == 200, r.text
        unit_id = r.json()["id"]

        new_name = f"TEST_I4_Renamed_{uuid.uuid4().hex[:6]}"
        new_loc = "Renamed Location"
        r = requests.put(f"{API}/developer/projects/{pid}",
                         json={"name": new_name, "location": new_loc},
                         headers=_h(dev_token), timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["name"] == new_name
        assert r.json()["location"] == new_loc

        # Verify unit project_name updated
        pd = requests.get(f"{API}/projects/{pid}", timeout=10).json()
        u = next((x for x in pd["units"] if x["id"] == unit_id), None)
        assert u is not None
        assert u.get("project_name") == new_name, f"unit project_name not synced: {u.get('project_name')}"

    def test_edit_project_invalid_program_400(self, dev_token):
        r = requests.put(f"{API}/developer/projects/{pytest.i4_project_id}",
                         json={"program": "INVALID"},
                         headers=_h(dev_token), timeout=10)
        assert r.status_code == 400


# --------- DP termin order enforcement ---------
class TestDpTermins:
    def test_full_dp_termin_flow(self, dev_token, consumer_token):
        # Create fresh project + unit + booking
        r = requests.post(f"{API}/developer/projects", json={
            "name": f"TEST_I4_DP_{uuid.uuid4().hex[:6]}",
            "location": "DP", "address_detail": "DP",
            "description": "dp", "program": "KOMERSIAL",
        }, headers=_h(dev_token), timeout=15)
        assert r.status_code == 200
        pid = r.json()["id"]

        r = requests.post(f"{API}/developer/units", json={
            "project_id": pid, "type": "TEST_I4_DP",
            "block": "T", "number": str(uuid.uuid4().int)[:4],
            "price": 300000000, "land_area": 60, "building_area": 30,
        }, headers=_h(dev_token), timeout=15)
        assert r.status_code == 200
        unit_id = r.json()["id"]

        r = requests.post(f"{API}/bookings", headers=_h(consumer_token), json={
            "unit_id": unit_id, "program": "FLPP", "dp_percent": 10,
            "tenor_years": 15, "payment_method": "VA_BTN",
        }, timeout=15)
        assert r.status_code == 200, r.text
        booking = r.json()
        bid = booking["id"]
        dp_amount = booking["dp_amount"]
        # Booking must include 3 termins
        termins = booking.get("dp_termins")
        assert termins and len(termins) == 3
        assert sum(t["amount"] for t in termins) == int(round(dp_amount))
        assert booking["dp_payment_status"] == "pending"

        # Pay booking fee
        r = requests.post(f"{API}/payments/webhook", json={
            "booking_id": bid, "status": "paid"
        }, timeout=10)
        assert r.status_code == 200

        # Developer SPR approve
        sig = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode()
        r = requests.post(f"{API}/bookings/{bid}/spr/approve",
                          headers=_h(dev_token), json={"signature": sig}, timeout=30)
        assert r.status_code == 200, r.text

        # Try termin 2 before termin 1 -> 400
        r = requests.post(f"{API}/bookings/{bid}/pay-dp?termin_no=2",
                          headers=_h(consumer_token), timeout=10)
        assert r.status_code == 400, f"Expected 400, got {r.status_code} {r.text}"

        # Pay termin 1
        r = requests.post(f"{API}/bookings/{bid}/pay-dp?termin_no=1",
                          headers=_h(consumer_token), timeout=10)
        assert r.status_code == 200, r.text
        pay = r.json()
        assert pay["kind"] == "dp_termin"
        assert pay["termin_no"] == 1
        assert pay["amount"] == termins[0]["amount"]

        r = requests.post(f"{API}/payments/webhook", json={
            "booking_id": bid, "status": "paid", "kind": "dp_termin", "termin_no": 1
        }, timeout=10)
        assert r.status_code == 200
        assert r.json()["dp_payment_status"] == "partial"

        # Termin 1 already paid -> 400
        r = requests.post(f"{API}/bookings/{bid}/pay-dp?termin_no=1",
                          headers=_h(consumer_token), timeout=10)
        assert r.status_code == 400

        # Pay termin 2
        r = requests.post(f"{API}/bookings/{bid}/pay-dp?termin_no=2",
                          headers=_h(consumer_token), timeout=10)
        assert r.status_code == 200
        r = requests.post(f"{API}/payments/webhook", json={
            "booking_id": bid, "status": "paid", "kind": "dp_termin", "termin_no": 2
        }, timeout=10)
        assert r.status_code == 200
        assert r.json()["dp_payment_status"] == "partial"

        # Pay termin 3 -> fully paid
        r = requests.post(f"{API}/bookings/{bid}/pay-dp?termin_no=3",
                          headers=_h(consumer_token), timeout=10)
        assert r.status_code == 200
        r = requests.post(f"{API}/payments/webhook", json={
            "booking_id": bid, "status": "paid", "kind": "dp_termin", "termin_no": 3
        }, timeout=10)
        assert r.status_code == 200
        assert r.json()["dp_payment_status"] == "paid"
        assert r.json()["remaining"] == 0

        # Verify booking record
        b = requests.get(f"{API}/bookings/{bid}", headers=_h(consumer_token), timeout=10).json()
        assert b["dp_payment_status"] == "paid"
        assert b["dp_paid_amount"] == int(round(dp_amount))
        assert all(t["status"] == "paid" for t in b["dp_termins"])
