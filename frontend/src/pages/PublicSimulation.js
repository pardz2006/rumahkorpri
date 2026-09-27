import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, rupiah, LOGO_URL } from "../lib/api";
import { Button } from "../components/ui/button";
import { Calculator, Download, Loader2, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export default function PublicSimulation() {
  const { token } = useParams();
  const [sim, setSim] = useState(null);
  const [err, setErr] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api.get(`/public/simulations/${token}`)
      .then((r) => setSim(r.data))
      .catch(() => setErr(true));
  }, [token]);

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.post("/kpr/simulate/pdf", {
        price: sim.price, dp_percent: sim.dp_percent, tenor_years: sim.tenor_years, program: sim.program,
      }, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = "simulasi-kpr.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("PDF simulasi diunduh");
    } catch (e) { toast.error("Gagal mengunduh PDF"); }
    finally { setDownloading(false); }
  };

  if (err) {
    return (
      <div className="min-h-screen grid place-items-center bg-[hsl(var(--background))] px-4">
        <div className="text-center">
          <Calculator className="h-12 w-12 text-slate-300 mx-auto" />
          <h1 className="font-heading text-2xl font-bold text-slate-800 mt-4">Simulasi tidak ditemukan</h1>
          <p className="text-slate-500 mt-1">Tautan mungkin salah atau sudah dihapus.</p>
          <Button asChild className="mt-5 bg-[hsl(var(--primary))]"><Link to="/">Ke Beranda</Link></Button>
        </div>
      </div>
    );
  }

  if (!sim) {
    return <div className="min-h-screen grid place-items-center bg-[hsl(var(--background))]"><Loader2 className="h-8 w-8 animate-spin text-[hsl(var(--primary))]" /></div>;
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--background))]">
      <header className="bg-[hsl(var(--primary))] grain">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 text-white">
            <div className="h-9 w-9 rounded-lg bg-white grid place-items-center p-1"><img src={LOGO_URL} alt="Logo Rumah KORPRI" className="h-full w-full object-contain" /></div>
            <div>
              <span className="font-heading font-bold text-xl bg-white rounded-lg px-3 py-1"><span className="text-[#1E3A8A]">RUMAH</span> <span className="text-[#D4AF37]">KORPRI</span></span>
              <p className="text-white/70 text-xs">Pemesanan & CRM KPR</p>
            </div>
          </Link>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        <p className="text-sm text-[hsl(var(--accent))] font-semibold">SIMULASI KPR DIBAGIKAN</p>
        <h1 data-testid="public-sim-label" className="font-heading text-3xl font-bold text-slate-800 mt-1">{sim.label}</h1>
        {sim.shared_by && <p className="text-slate-500 mt-1">Dibagikan oleh {sim.shared_by}</p>}

        <div className="mt-6 grid sm:grid-cols-3 gap-3">
          <Stat label="Harga rumah" value={rupiah(sim.price)} />
          <Stat label={`Uang muka (${sim.dp_percent}%)`} value={rupiah(sim.dp_amount)} />
          <Stat label="Plafon KPR" value={rupiah(sim.loan_amount)} />
        </div>

        <div className="mt-4 bg-white rounded-xl border border-slate-200/80 shadow-sm p-6">
          <p className="text-xs text-slate-500">Estimasi angsuran per bulan</p>
          <p className="font-heading text-4xl font-bold text-[hsl(var(--primary))] mt-1">{rupiah(sim.first_installment)}</p>
          <p className="text-sm text-slate-500 mt-1">{sim.program_label} · tenor {sim.tenor_years} tahun</p>

          <div className="mt-5 space-y-1.5">
            {sim.schedule?.map((s, i) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-slate-500">{s.phase} · thn {s.from_year}-{s.to_year} · {s.rate}%</span>
                <span className="font-medium text-slate-700">{rupiah(s.monthly)}</span>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 mt-5 pt-5 border-t border-slate-100">
            <div><p className="text-xs text-slate-400">Total bunga (estimasi)</p><p className="font-semibold text-slate-800">{rupiah(sim.total_interest)}</p></div>
            <div><p className="text-xs text-slate-400">Total pembayaran</p><p className="font-semibold text-slate-800">{rupiah(sim.total_paid)}</p></div>
          </div>

          <Button data-testid="public-sim-pdf" onClick={downloadPdf} disabled={downloading} className="w-full mt-5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
            {downloading ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Download className="h-4 w-4 mr-1.5" />}
            Unduh PDF
          </Button>
        </div>

        <div className="mt-6 bg-[hsl(var(--secondary))]/50 rounded-xl p-5 flex items-center justify-between">
          <p className="text-sm text-slate-600">Tertarik memiliki rumah ASN bersubsidi?</p>
          <Button asChild variant="outline" className="border-[hsl(var(--primary))] text-[hsl(var(--primary))]">
            <Link to="/">Lihat Proyek <ArrowRight className="h-4 w-4 ml-1" /></Link>
          </Button>
        </div>
        <p className="text-xs text-slate-400 mt-4 text-center">Estimasi bersifat indikatif. Angka final mengikuti ketentuan bank.</p>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="font-heading font-bold text-slate-800 mt-0.5">{value}</p>
    </div>
  );
}
