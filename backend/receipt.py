"""Generate a payment receipt (Kuitansi) PDF for booking fee or DP termin."""
import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def _rupiah(v) -> str:
    try:
        return "Rp " + f"{int(v):,}".replace(",", ".")
    except Exception:
        return f"Rp {v}"


def generate_receipt_pdf(booking: dict, unit: dict, project: dict, user: dict,
                         kind: str, termin: dict | None, ref: str | None) -> bytes:
    buf = io.BytesIO()
    w, h = A5
    c = canvas.Canvas(buf, pagesize=A5)
    green = colors.HexColor("#0F5132")
    accent = colors.HexColor("#C05621")

    c.setFillColor(green)
    c.rect(0, h - 28 * mm, w, 28 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(15 * mm, h - 15 * mm, "KUITANSI PEMBAYARAN")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, h - 22 * mm, "rumahkorpri.com — Pemesanan Rumah & CRM KPR")

    if kind == "dp_termin":
        title = f"Uang Muka (DP) — Termin ke-{termin.get('no')}"
        amount = termin.get("amount", 0)
    else:
        title = "Booking Fee / Uang Tanda Jadi"
        amount = booking.get("booking_fee", 0)

    y = h - 40 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y, f"No. Ref: {ref or '-'}")
    c.drawRightString(w - 15 * mm, y, datetime.now(timezone.utc).strftime("%d %B %Y"))
    y -= 10 * mm

    def row(label, value):
        nonlocal y
        c.setFont("Helvetica", 9)
        c.drawString(15 * mm, y, label)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(55 * mm, y, f": {value}")
        y -= 6.5 * mm

    row("Telah diterima dari", user.get("name", "-"))
    row("Untuk pembayaran", title)
    row("Proyek", project.get("name", "-"))
    row("Unit", f"{unit.get('type','-')} · Blok {unit.get('block','-')}/{unit.get('number','-')}")
    row("Metode", booking.get("payment_method", "-"))
    row("No. SPR", booking.get("spr_number", "-"))

    y -= 4 * mm
    c.setFillColor(accent)
    c.rect(15 * mm, y - 10 * mm, w - 30 * mm, 14 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(19 * mm, y - 5 * mm, "TERBAYAR")
    c.drawRightString(w - 19 * mm, y - 5 * mm, _rupiah(amount))

    c.setFillColor(colors.HexColor("#4A5568"))
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawString(15 * mm, 12 * mm,
                 "Kuitansi ini diterbitkan otomatis oleh sistem dan sah sebagai bukti pembayaran (simulasi).")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
