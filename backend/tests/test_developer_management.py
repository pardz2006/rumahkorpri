"""Tests for new developer project & unit management endpoints."""
import os
import uuid
import base64
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

# Tiny 1x1 PNG data URL
TINY_PNG = "data:image/png;base64," + base64.b64encode(
    bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000000000200015E5DFB7F0000000049454E44AE426082")
).decode()


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def dev_token():
    return _login("developer@rumahkorpri.com", "developer123")


@pytest.fixture(scope="module")
def consumer_token():
    return _login("consumer@rumahkorpri.com", "consumer123")


def _h(t):
    return {"Authorization": f"Bearer {t}"}


class TestDeveloperProjectUnitManagement:
    def test_create_project_as_developer(self, dev_token):
        payload = {
            "name": f"TEST_Proyek_{uuid.uuid4().hex[:6]}",
            "location": "Test City",
            "address_detail": "Jl. Test No.1",
            "developer_name": "PT Test Developer",
            "description": "Perumahan uji coba",
            "image": TINY_PNG,
            "program": "KOMERSIAL",
        }
        r = requests.post(f"{API}/developer/projects", json=payload, headers=_h(dev_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["location"] == "Test City"
        assert "id" in data
        pytest.project_id = data["id"]

        # Verify appears in public list
        pub = requests.get(f"{API}/projects", timeout=10).json()
        assert any(p["id"] == data["id"] for p in pub)

    def test_create_unit_as_developer(self, dev_token):
        assert hasattr(pytest, "project_id"), "prior project test must run first"
        payload = {
            "project_id": pytest.project_id,
            "type": "TEST_Tipe 36/72",
            "block": "T",
            "number": "01",
            "price": 275000000,
            "land_area": 72,
            "building_area": 36,
            "address_detail": "Blok T No.01",
            "image_front": TINY_PNG,
            "image_layout": TINY_PNG,
            "image_siteplan": TINY_PNG,
        }
        r = requests.post(f"{API}/developer/units", json=payload, headers=_h(dev_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "available"
        assert data["type"] == payload["type"]
        assert data["image_front"].startswith("data:image/png")
        pytest.unit_id = data["id"]

        # Verify appears in project detail
        pd = requests.get(f"{API}/projects/{pytest.project_id}", timeout=10).json()
        assert any(u["id"] == data["id"] and u["status"] == "available" for u in pd["units"])

    def test_consumer_cannot_create_project(self, consumer_token):
        r = requests.post(f"{API}/developer/projects", json={
            "name": "TEST_forbidden", "location": "X", "program": "FLPP"
        }, headers=_h(consumer_token), timeout=10)
        assert r.status_code == 403

    def test_consumer_cannot_create_unit(self, consumer_token):
        r = requests.post(f"{API}/developer/units", json={
            "project_id": getattr(pytest, "project_id", "000000000000000000000000"),
            "type": "X", "block": "X", "number": "1", "price": 100000000
        }, headers=_h(consumer_token), timeout=10)
        assert r.status_code == 403

    def test_unauthenticated_cannot_create(self):
        r = requests.post(f"{API}/developer/projects", json={"name": "x", "location": "x"}, timeout=10)
        assert r.status_code in (401, 403)

    def test_create_unit_invalid_project(self, dev_token):
        r = requests.post(f"{API}/developer/units", json={
            "project_id": "000000000000000000000000",
            "type": "X", "block": "X", "number": "1", "price": 100000000
        }, headers=_h(dev_token), timeout=10)
        assert r.status_code == 404
