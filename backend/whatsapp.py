"""Twilio WhatsApp sender. Falls back to 'simulasi' when credentials are absent."""
import os

from twilio.rest import Client

TWILIO_SID = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
TWILIO_TOKEN = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
TWILIO_WHATSAPP_FROM = (os.environ.get("TWILIO_WHATSAPP_FROM") or "").strip()

_client = None


def is_enabled() -> bool:
    return bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_WHATSAPP_FROM)


def _get_client():
    global _client
    if _client is None and TWILIO_SID and TWILIO_TOKEN:
        _client = Client(TWILIO_SID, TWILIO_TOKEN)
    return _client


def normalize(phone: str):
    if not phone:
        return None
    p = phone.strip().replace(" ", "").replace("-", "")
    if p in ("-", ""):
        return None
    if p.startswith("+"):
        return p
    if p.startswith("62"):
        return "+" + p
    if p.startswith("0"):
        return "+62" + p[1:]
    return "+" + p


def send_whatsapp(to_phone: str, body: str) -> dict:
    """Kirim pesan WhatsApp. Return {status, sid, error, simulated}."""
    if not is_enabled():
        return {"status": "simulated", "sid": None, "error": None, "simulated": True}
    to = normalize(to_phone)
    if not to:
        return {"status": "failed", "sid": None, "error": "Nomor WhatsApp tidak valid", "simulated": False}
    frm = TWILIO_WHATSAPP_FROM
    if not frm.startswith("whatsapp:"):
        frm = "whatsapp:" + (frm if frm.startswith("+") else "+" + frm)
    try:
        msg = _get_client().messages.create(from_=frm, to="whatsapp:" + to, body=body)
        return {"status": "sent", "sid": msg.sid, "error": None, "simulated": False}
    except Exception as e:
        return {"status": "failed", "sid": None, "error": str(e), "simulated": False}
