"""Tests for new KPR amortization, PDF download, WhatsApp fallback, and follow-up."""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "pardz2006@gmail.com", "password": "korpri123"}
CONSUMER = {"email": "consumer@rumahkorpri.com", "password": "consumer123"}
DEVELOPER = {"email": "developer@rumahkorpri.com", "password": "developer123"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    return j.get("access_token") or j.get("token")


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


# ----- KPR simulate: tiered rates -----
def test_simulate_komersial_tiered():
    r = requests.post(f"{API}/kpr/simulate", json={
        "price": 500_000_000, "dp_percent": 20, "tenor_years": 20, "program": "KOMERSIAL"
    }, timeout=30)
    assert r.status_code == 200
    data = r.json()
    sched = data["schedule"]
    # First phase must be 2.65 fix for years 1-3
    assert sched[0]["rate"] == 2.65
    assert sched[0]["from_year"] == 1 and sched[0]["to_year"] == 3
    # All rates must be <= cap 9.99
    for p in sched:
        assert p["rate"] <= 9.99
    # Contains rising rates
    rates = [p["rate"] for p in sched]
    assert rates == sorted(rates)  # non-decreasing


def test_simulate_flpp_flat():
    r = requests.post(f"{API}/kpr/simulate", json={
        "price": 200_000_000, "dp_percent": 10, "tenor_years": 15, "program": "FLPP"
    }, timeout=30)
    assert r.status_code == 200
    data = r.json()
    sched = data["schedule"]
    assert len(sched) == 1
    assert sched[0]["rate"] == 5.0
    assert sched[0]["from_year"] == 1 and sched[0]["to_year"] == 15


# ----- Amortization -----
def test_amortization_schedule_komersial():
    payload = {"price": 500_000_000, "dp_percent": 20, "tenor_years": 20, "program": "KOMERSIAL"}
    r = requests.post(f"{API}/kpr/amortization", json=payload, timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert len(d["months"]) == 20 * 12
    m1 = d["months"][0]
    for k in ("month", "year", "rate", "installment", "interest", "principal", "balance"):
        assert k in m1
    # Verify month 1 interest = round(loan * monthly_rate)
    loan = d["loan_amount"]
    rate1 = m1["rate"] / 100 / 12
    assert m1["interest"] == round(loan * rate1)
    # Balance should decrease and end near 0
    last = d["months"][-1]
    assert last["balance"] <= 10_000  # rounding tolerance
    # yearly summary
    assert len(d["yearly"]) == 20
    assert d["total_interest"] > 0
    assert d["total_paid"] > loan


# ----- PDF -----
def test_simulate_pdf():
    r = requests.post(f"{API}/kpr/simulate/pdf", json={
        "price": 400_000_000, "dp_percent": 15, "tenor_years": 15, "program": "KOMERSIAL"
    }, timeout=60)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000


# ----- WhatsApp status -----
def test_whatsapp_status_simulasi():
    tok = _login(ADMIN)
    r = requests.get(f"{API}/whatsapp/status", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["enabled"] is False
    assert d["channel"] == "simulasi"


def test_whatsapp_status_requires_auth():
    r = requests.get(f"{API}/whatsapp/status", timeout=30)
    assert r.status_code in (401, 403)


# ----- Follow-up: requires SPR issued + missing doc -----
def test_followup_simulasi_fallback():
    """Find an existing booking with SPR issued and a missing/invalid doc, then
    call /followup. If none available, create the state via existing endpoints.
    Verify channel:'simulasi' response and wa_log entry."""
    admin = _login(ADMIN)
    # 1. Try to find candidate booking already in that state
    r = requests.get(f"{API}/bookings", headers=_hdr(admin), timeout=30)
    assert r.status_code == 200
    bookings = r.json()

    candidate = None
    for b in bookings:
        if b.get("spr_status") != "issued":
            continue
        docs = b.get("documents") or []
        missing = [d for d in docs if d.get("status") in ("missing", "invalid")]
        if missing:
            candidate = b
            break

    if not candidate:
        # Create the precondition via full flow
        consumer_tok = _login(CONSUMER)
        # Pick an available Komersial unit
        r_proj = requests.get(f"{API}/projects", timeout=30)
        assert r_proj.status_code == 200
        unit_id = None
        for p in r_proj.json():
            for u in p.get("units", []):
                if u.get("status") == "available":
                    unit_id = u["id"]
                    break
            if unit_id:
                break
        assert unit_id, "No available unit to create booking"
        r_b = requests.post(f"{API}/bookings", headers=_hdr(consumer_tok), json={
            "unit_id": unit_id, "program": "KOMERSIAL",
            "dp_percent": 20, "tenor_years": 15, "payment_method": "QRIS"
        }, timeout=30)
        assert r_b.status_code == 200, r_b.text
        bid = r_b.json()["id"]
        # Pay booking fee via webhook
        r_pay = requests.post(f"{API}/payments/webhook", json={
            "booking_id": bid, "status": "paid", "kind": "booking_fee"
        }, timeout=30)
        assert r_pay.status_code == 200, r_pay.text
        # Approve SPR as admin
        r_appr = requests.post(f"{API}/bookings/{bid}/spr/approve",
                               headers=_hdr(admin), json={"signature": None}, timeout=60)
        assert r_appr.status_code == 200, r_appr.text
        candidate = {"id": bid}

    bid = candidate["id"]
    # Snapshot wa_logs count before
    r_logs = requests.get(f"{API}/wa-logs", headers=_hdr(admin), timeout=30)
    logs_before = len(r_logs.json()) if r_logs.status_code == 200 else 0

    r = requests.post(f"{API}/bookings/{bid}/followup", headers=_hdr(admin), timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ok"] is True
    assert d["channel"] == "simulasi"
    assert d["wa_status"] == "simulated"
    assert isinstance(d.get("missing"), list) and len(d["missing"]) > 0

    # Verify wa_log entry created
    r_logs2 = requests.get(f"{API}/wa-logs", headers=_hdr(admin), timeout=30)
    assert r_logs2.status_code == 200
    logs_after = r_logs2.json()
    assert len(logs_after) > logs_before
    latest = logs_after[0]
    assert latest["channel"] == "simulasi"
    assert latest["status"] == "simulated"
    assert "template" in latest
