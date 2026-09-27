"""KPR (mortgage) simulation logic for FLPP subsidized and Komersial programs.

Komersial memakai skema promo KORPRI: bunga 2,65% fixed selama 3 tahun,
kemudian naik bertahap sampai maksimal 9,99% (cap floating).
"""

# Program defaults.
# `rate_tiers`: daftar tahap bunga berurutan. `years=None` berarti tahap terakhir
# menutupi sisa tenor. Bunga naik bertahap dan tidak melebihi cap terakhir.
PROGRAMS = {
    "FLPP": {
        "label": "FLPP (Subsidi Pemerintah)",
        "max_price": 240000000,
        "rate_tiers": [
            {"rate": 5.0, "years": None},  # flat subsidi seumur tenor
        ],
    },
    "KOMERSIAL": {
        "label": "KPR Komersial (Promo KORPRI)",
        "max_price": None,
        "rate_tiers": [
            {"rate": 2.65, "years": 3},     # fixed 3 tahun
            {"rate": 5.00, "years": 2},     # tahun 4-5
            {"rate": 7.50, "years": 3},     # tahun 6-8
            {"rate": 9.99, "years": None},  # tahun 9+ (floating, cap maks.)
        ],
    },
}


def annuity_payment(principal: float, annual_rate: float, months: int) -> float:
    if months <= 0:
        return 0.0
    r = annual_rate / 100 / 12
    if r == 0:
        return principal / months
    return principal * r / (1 - (1 + r) ** (-months))


def _remaining_after(principal: float, annual_rate: float, installment: float, months: int) -> float:
    """Sisa pokok setelah `months` pembayaran `installment` pada bunga tahunan tertentu."""
    r = annual_rate / 100 / 12
    if r == 0:
        return max(0.0, principal - installment * months)
    bal = principal * (1 + r) ** months - installment * (((1 + r) ** months - 1) / r)
    return max(0.0, bal)


def simulate(price: float, dp_percent: float, tenor_years: int, program: str):
    program = program.upper()
    cfg = PROGRAMS.get(program, PROGRAMS["KOMERSIAL"])

    dp_percent = max(0.0, min(dp_percent, 100.0))
    tenor_years = max(1, min(int(tenor_years), 30))

    dp_amount = round(price * dp_percent / 100)
    loan = price - dp_amount
    total_months = tenor_years * 12

    # Bangun tahapan berdasarkan tenor.
    tiers = cfg["rate_tiers"]
    phases = []
    year_cursor = 1
    remaining = loan

    for idx, tier in enumerate(tiers):
        if year_cursor > tenor_years:
            break
        is_last = tier.get("years") is None or idx == len(tiers) - 1
        if is_last:
            phase_to_year = tenor_years
        else:
            phase_to_year = min(tenor_years, year_cursor + tier["years"] - 1)

        months_elapsed = (year_cursor - 1) * 12
        remaining_months = total_months - months_elapsed
        # Re-amortisasi sisa pokok atas sisa tenor pada bunga tahap ini.
        installment = annuity_payment(remaining, tier["rate"], remaining_months)

        phase_months = (phase_to_year - year_cursor + 1) * 12
        rate = tier["rate"]
        if idx == 0:
            phase_label = "Fix"
        elif is_last:
            phase_label = "Floating (maks.)"
        else:
            phase_label = "Bertahap"

        phases.append({
            "phase": phase_label,
            "rate": rate,
            "from_year": year_cursor,
            "to_year": phase_to_year,
            "monthly": round(installment),
        })

        remaining = _remaining_after(remaining, tier["rate"], installment, phase_months)
        year_cursor = phase_to_year + 1
        if phase_to_year >= tenor_years:
            break

    return {
        "program": program,
        "program_label": cfg["label"],
        "price": price,
        "dp_percent": dp_percent,
        "dp_amount": dp_amount,
        "loan_amount": loan,
        "tenor_years": tenor_years,
        "schedule": phases,
        "first_installment": phases[0]["monthly"],
    }


def amortization_schedule(price: float, dp_percent: float, tenor_years: int, program: str):
    """Rincian angsuran bulan-per-bulan (pokok, bunga, sisa pokok) berdasar skema tahapan."""
    sim = simulate(price, dp_percent, tenor_years, program)
    balance = float(sim["loan_amount"])
    total_months = sim["tenor_years"] * 12
    months = []
    month_no = 0

    for ph in sim["schedule"]:
        rate_m = ph["rate"] / 100 / 12
        installment = ph["monthly"]
        phase_months = (ph["to_year"] - ph["from_year"] + 1) * 12
        for _ in range(phase_months):
            month_no += 1
            interest = round(balance * rate_m)
            principal = installment - interest
            if month_no == total_months or principal > balance:
                # bulan terakhir melunasi sisa pokok persis sampai nol
                principal = round(balance)
                installment = interest + principal
            balance = max(0.0, balance - principal)
            months.append({
                "month": month_no,
                "year": (month_no - 1) // 12 + 1,
                "rate": ph["rate"],
                "installment": installment,
                "interest": interest,
                "principal": round(principal),
                "balance": round(balance),
            })

    yearly = {}
    for r in months:
        y = yearly.setdefault(r["year"], {
            "year": r["year"], "rate": r["rate"],
            "interest": 0, "principal": 0, "installment_total": 0, "end_balance": 0,
        })
        y["interest"] += r["interest"]
        y["principal"] += r["principal"]
        y["installment_total"] += r["installment"]
        y["end_balance"] = r["balance"]
    yearly_list = [yearly[k] for k in sorted(yearly)]

    total_interest = sum(r["interest"] for r in months)
    total_paid = sum(r["installment"] for r in months)

    return {
        **sim,
        "months": months,
        "yearly": yearly_list,
        "total_interest": total_interest,
        "total_paid": total_paid,
    }
