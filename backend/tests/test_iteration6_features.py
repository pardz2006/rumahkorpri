"""Iteration 6: saved simulations, editable profile+project sort, Twilio test-send."""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

CONSUMER = ("consumer@rumahkorpri.com", "consumer123")
ADMIN = ("pardz2006@gmail.com", "korpri123")
DEV = ("developer@rumahkorpri.com", "developer123")


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def consumer_token():
    return _login(*CONSUMER)


@pytest.fixture(scope="module")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def dev_token():
    return _login(*DEV)


def h(t):
    return {"Authorization": f"Bearer {t}"}


# ---------- Saved simulations ----------
class TestSimulations:
    def test_save_sim(self, consumer_token):
        r = requests.post(f"{API}/simulations", headers=h(consumer_token), json={
            "price": 500_000_000, "dp_percent": 10, "tenor_years": 15, "program": "KOMERSIAL",
            "label": "TEST_sim_1"
        })
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("id", "label", "first_installment", "total_interest", "total_paid", "schedule"):
            assert k in d, f"missing key {k}"
        assert d["label"] == "TEST_sim_1"
        assert isinstance(d["schedule"], list) and len(d["schedule"]) > 0
        pytest.saved_sim_id = d["id"]

    def test_list_only_own(self, consumer_token, admin_token):
        r = requests.get(f"{API}/simulations", headers=h(consumer_token))
        assert r.status_code == 200
        sims = r.json()
        assert any(s["id"] == pytest.saved_sim_id for s in sims)
        # admin's list shouldn't include consumer's sim
        r2 = requests.get(f"{API}/simulations", headers=h(admin_token))
        assert r2.status_code == 200
        assert not any(s["id"] == pytest.saved_sim_id for s in r2.json())

    def test_delete_others_forbidden_404(self, admin_token):
        r = requests.delete(f"{API}/simulations/{pytest.saved_sim_id}", headers=h(admin_token))
        assert r.status_code == 404

    def test_delete_missing_404(self, consumer_token):
        r = requests.delete(f"{API}/simulations/507f1f77bcf86cd799439011", headers=h(consumer_token))
        assert r.status_code == 404

    def test_delete_own(self, consumer_token):
        r = requests.delete(f"{API}/simulations/{pytest.saved_sim_id}", headers=h(consumer_token))
        assert r.status_code == 200
        # verify removed
        r2 = requests.get(f"{API}/simulations", headers=h(consumer_token))
        assert not any(s["id"] == pytest.saved_sim_id for s in r2.json())


# ---------- Profile + project sort ----------
class TestProfileDomicile:
    def _patch(self, tok, city, province):
        return requests.patch(f"{API}/profile", headers=h(tok),
                              json={"city": city, "province": province, "phone": "+628123456789"})

    def _project_names(self, tok):
        r = requests.get(f"{API}/projects", headers=h(tok))
        assert r.status_code == 200
        return [p["name"] for p in r.json()]

    def test_patch_depok_bumi_first(self, consumer_token):
        r = self._patch(consumer_token, "Depok", "Jawa Barat")
        assert r.status_code == 200
        d = r.json()
        assert d["city"] == "Depok"
        assert d["phone"] == "+628123456789"
        names = self._project_names(consumer_token)
        assert names, "no projects"
        # Bumi ASN Residence is in Depok, must come first
        bumi = next((i for i, n in enumerate(names) if "Bumi ASN" in n), -1)
        griya = next((i for i, n in enumerate(names) if "Griya KORPRI" in n), -1)
        assert bumi != -1 and bumi < griya if griya != -1 else bumi != -1, f"names={names}"

    def test_patch_bekasi_griya_first(self, consumer_token):
        r = self._patch(consumer_token, "Bekasi", "Jawa Barat")
        assert r.status_code == 200
        names = self._project_names(consumer_token)
        griya = next((i for i, n in enumerate(names) if "Griya KORPRI" in n), -1)
        bumi = next((i for i, n in enumerate(names) if "Bumi ASN" in n), -1)
        assert griya != -1 and (bumi == -1 or griya < bumi), f"names={names}"


# ---------- WhatsApp status + test send ----------
class TestWhatsApp:
    def test_status_enabled(self, admin_token):
        r = requests.get(f"{API}/whatsapp/status", headers=h(admin_token))
        assert r.status_code == 200
        d = r.json()
        assert d["enabled"] is True
        assert d["channel"] == "twilio"

    def test_test_send_admin_200(self, admin_token):
        r = requests.post(f"{API}/whatsapp/test", headers=h(admin_token),
                          json={"phone": "+628999999999"})
        assert r.status_code == 200, r.text
        d = r.json()
        # result shape: status/sid/error/simulated
        for k in ("status", "sid", "error", "simulated"):
            assert k in d, f"missing {k} in {d}"
        # trial account may fail; accept sent/failed but must not 500
        assert d["status"] in ("sent", "failed")

    def test_test_send_non_admin_403(self, dev_token):
        r = requests.post(f"{API}/whatsapp/test", headers=h(dev_token),
                          json={"phone": "+628999999999"})
        assert r.status_code == 403
