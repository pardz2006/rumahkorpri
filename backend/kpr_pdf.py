"""Generate a KPR simulation summary PDF (skema bunga + amortisasi tahunan)."""
import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def _rupiah(v) -> str:
    try:
        return "Rp " + f"{int(round(v)):,}".replace(",", ".")
    except Exception:
        return f"Rp {v}"


def generate_kpr_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    green = colors.HexColor("#0F5132")
    accent = colors.HexColor("#C05621")
    grey = colors.HexColor("#4A5568")

    # Header band
    c.setFillColor(green)
    c.rect(0, h - 34 * mm, w, 34 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, h - 16 * mm, "SIMULASI KREDIT PEMILIKAN RUMAH (KPR)")
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 23 * mm, "rumahkorpri.com — Sistem Pemesanan Rumah & CRM KPR KORPRI")
    c.drawString(20 * mm, h - 29 * mm, "Dokumen estimasi — bukan penawaran resmi bank.")

    y = h - 44 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, y, "Diterbitkan: " + datetime.now(timezone.utc).strftime("%d %B %Y %H:%M UTC"))
    y -= 9 * mm

    # Ringkasan input
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "A. Ringkasan Pembiayaan")
    c.setFillColor(colors.black)
    y -= 8 * mm

    def row(label, value):
        nonlocal y
        c.setFont("Helvetica", 9.5)
        c.drawString(24 * mm, y, label)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(75 * mm, y, ": " + str(value))
        y -= 6 * mm

    row("Program", data.get("program_label", "-"))
    row("Harga Rumah", _rupiah(data.get("price", 0)))
    row("Uang Muka (DP)", f"{data.get('dp_percent', 0):g}% · {_rupiah(data.get('dp_amount', 0))}")
    row("Plafon KPR", _rupiah(data.get("loan_amount", 0)))
    row("Tenor", f"{data.get('tenor_years', 0)} tahun")
    row("Angsuran awal", _rupiah(data.get("first_installment", 0)) + " / bulan")
    row("Total bunga (estimasi)", _rupiah(data.get("total_interest", 0)))
    row("Total pembayaran", _rupiah(data.get("total_paid", 0)))
    y -= 3 * mm

    # Skema tahapan bunga
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "B. Skema Tahapan Bunga")
    c.setFillColor(colors.black)
    y -= 8 * mm

    schedule = data.get("schedule", [])
    _table_header(c, y, ["Tahap", "Tahun", "Bunga", "Angsuran / bulan"],
                  [24, 62, 90, 118], green)
    y -= 6.5 * mm
    c.setFont("Helvetica", 9)
    for s in schedule:
        c.drawString(24 * mm, y, str(s.get("phase", "-")))
        c.drawString(62 * mm, y, f"{s.get('from_year')}-{s.get('to_year')}")
        c.drawString(90 * mm, y, f"{s.get('rate')}%")
        c.drawString(118 * mm, y, _rupiah(s.get("monthly", 0)))
        y -= 6 * mm
    y -= 4 * mm

    # Amortisasi tahunan
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "C. Amortisasi Tahunan (Pokok & Bunga)")
    c.setFillColor(colors.black)
    y -= 8 * mm

    cols = [22, 40, 62, 100, 138, 170]
    _table_header(c, y, ["Thn", "Bunga%", "Angsuran/th", "Pokok/th", "Bunga/th", "Sisa Pokok"],
                  cols, green)
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    for yr in data.get("yearly", []):
        if y < 22 * mm:
            c.showPage()
            y = h - 24 * mm
            _table_header(c, y, ["Thn", "Bunga%", "Angsuran/th", "Pokok/th", "Bunga/th", "Sisa Pokok"],
                          cols, green)
            y -= 6 * mm
            c.setFont("Helvetica", 8)
        c.drawString(cols[0] * mm, y, str(yr["year"]))
        c.drawString(cols[1] * mm, y, f"{yr['rate']}%")
        c.drawString(cols[2] * mm, y, _rupiah(yr["installment_total"]))
        c.drawString(cols[3] * mm, y, _rupiah(yr["principal"]))
        c.drawString(cols[4] * mm, y, _rupiah(yr["interest"]))
        c.drawString(cols[5] * mm, y, _rupiah(yr["end_balance"]))
        y -= 5.2 * mm

    c.setFillColor(grey)
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawString(20 * mm, 14 * mm,
                 "Estimasi dihitung dengan metode anuitas dan re-amortisasi tiap perubahan bunga. "
                 "Angka final mengikuti ketentuan bank.")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _table_header(c, y, labels, xs, color):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 8.5)
    for label, x in zip(labels, xs):
        c.drawString(x * mm, y, label)
    c.setStrokeColor(color)
    c.setLineWidth(0.4)
    c.line(20 * mm, y - 2 * mm, 190 * mm, y - 2 * mm)
    c.setFillColor(colors.black)
