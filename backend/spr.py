"""Generate the Surat Pemesanan Rumah (SPR) as a PDF, returned base64-encoded."""
import base64
import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def _rupiah(v) -> str:
    try:
        return "Rp " + f"{int(v):,}".replace(",", ".")
    except Exception:
        return f"Rp {v}"


def generate_spr_pdf(booking: dict, unit: dict, project: dict, user: dict,
                     signature_b64: str | None = None) -> str:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    green = colors.HexColor("#0F5132")
    accent = colors.HexColor("#C05621")

    # Header band
    c.setFillColor(green)
    c.rect(0, h - 40 * mm, w, 40 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20 * mm, h - 20 * mm, "SURAT PEMESANAN RUMAH (SPR)")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, h - 27 * mm, "Sistem Pemesanan Rumah & CRM Rumah KORPRI")
    c.drawString(20 * mm, h - 33 * mm, f"No. SPR: {booking.get('spr_number', '-')}")

    y = h - 52 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    tgl = datetime.now(timezone.utc).strftime("%d %B %Y")
    c.drawString(20 * mm, y, f"Diterbitkan pada: {tgl}")
    y -= 10 * mm

    def section(title):
        nonlocal y
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, title)
        c.setFillColor(colors.black)
        y -= 7 * mm

    def row(label, value):
        nonlocal y
        c.setFont("Helvetica", 10)
        c.drawString(24 * mm, y, f"{label}")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(80 * mm, y, f": {value}")
        y -= 6 * mm

    section("A. Data Pemesan")
    row("Nama", user.get("name", "-"))
    row("NIK/NIP", user.get("nik") or "-")
    row("Instansi", user.get("instansi") or "-")
    row("No. WhatsApp", user.get("phone") or "-")
    row("Email", user.get("email", "-"))
    row("Penghasilan/bln", _rupiah(user.get("monthly_income") or 0))
    y -= 4 * mm

    section("B. Data Unit")
    row("Proyek", project.get("name", "-"))
    row("Lokasi", project.get("location", "-"))
    row("Tipe Rumah", unit.get("type", "-"))
    row("Blok / No.", f"{unit.get('block', '-')} / {unit.get('number', '-')}")
    row("Luas (LT/LB)", f"{unit.get('land_area','-')} / {unit.get('building_area','-')} m2")
    row("Harga Unit", _rupiah(unit.get("price", 0)))
    y -= 4 * mm

    section("C. Pembayaran Tanda Jadi")
    row("Metode", booking.get("payment_method", "-"))
    row("Booking Fee", _rupiah(booking.get("booking_fee", 0)))
    row("Status", booking.get("payment_status", "-").upper())
    row("Ref. Bayar", booking.get("payment_ref", "-"))
    y -= 8 * mm

    # Signature block
    c.setFont("Helvetica", 10)
    c.drawString(120 * mm, y, "Disetujui oleh Developer,")
    if signature_b64:
        try:
            from reportlab.lib.utils import ImageReader
            img_data = base64.b64decode(signature_b64.split(",")[-1])
            img = ImageReader(io.BytesIO(img_data))
            c.drawImage(img, 120 * mm, y - 30 * mm, width=45 * mm, height=25 * mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    y -= 34 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(120 * mm, y, project.get("developer_name", "Mitra Developer"))

    c.setFillColor(colors.HexColor("#4A5568"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(20 * mm, 15 * mm,
                 "Dokumen ini diterbitkan otomatis oleh sistem rumahkorpri.com dan sah tanpa tanda tangan basah.")

    c.showPage()
    c.save()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
