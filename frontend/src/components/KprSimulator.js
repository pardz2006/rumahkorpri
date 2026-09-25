import React, { useState, useEffect, useCallback } from "react";
import { api, rupiah } from "../lib/api";
import { Slider } from "./ui/slider";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { Calculator, Download, Table2, Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";

export function KprSimulator({ price, defaultProgram = "FLPP", compact = false }) {
  const [program, setProgram] = useState(defaultProgram);
  const [dp, setDp] = useState(10);
  const [tenor, setTenor] = useState(15);
  const [result, setResult] = useState(null);
  const [amort, setAmort] = useState(null);
  const [showAmort, setShowAmort] = useState(false);
  const [loadingAmort, setLoadingAmort] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [saving, setSaving] = useState(false);
  const { user } = useAuth();

  const payload = { price, dp_percent: dp, tenor_years: tenor, program };

  const run = useCallback(async () => {
    try {
      const { data } = await api.post("/kpr/simulate", {
        price, dp_percent: dp, tenor_years: tenor, program,
      });
      setResult(data);
    } catch (e) { /* ignore */ }
    // reset amortisasi bila parameter berubah
    setAmort(null);
    setShowAmort(false);
  }, [price, dp, tenor, program]);

  useEffect(() => { run(); }, [run]);

  const toggleAmort = async () => {
    if (showAmort) { setShowAmort(false); return; }
    if (amort) { setShowAmort(true); return; }
    setLoadingAmort(true);
    try {
      const { data } = await api.post("/kpr/amortization", payload);
      setAmort(data);
      setShowAmort(true);
    } catch (e) {
      toast.error("Gagal memuat tabel amortisasi");
    } finally {
      setLoadingAmort(false);
    }
  };

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const res = await api.post("/kpr/simulate/pdf", payload, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "simulasi-kpr.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Simulasi KPR diunduh (PDF)");
    } catch (e) {
      toast.error("Gagal mengunduh PDF");
    } finally {
      setDownloading(false);
    }
  };

  const saveSim = async () => {
    setSaving(true);
    try {
      await api.post("/simulations", payload);
      toast.success("Simulasi disimpan ke Riwayat di portal Anda");
    } catch (e) {
      toast.error("Gagal menyimpan simulasi");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-testid="kpr-simulator" className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-9 w-9 rounded-lg bg-[hsl(var(--secondary))] grid place-items-center">
          <Calculator className="h-5 w-5 text-[hsl(var(--primary))]" />
        </div>
        <div>
          <p className="font-heading font-semibold text-slate-800">Simulasi KPR</p>
          <p className="text-xs text-slate-500">Estimasi angsuran bulanan</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        {["FLPP", "KOMERSIAL"].map((p) => (
          <button
            key={p}
            data-testid={`sim-program-${p}`}
            onClick={() => setProgram(p)}
            className={`text-sm font-medium rounded-lg py-2 border transition-colors ${
              program === p
                ? "bg-[hsl(var(--primary))] text-white border-transparent"
                : "bg-white text-slate-600 border-slate-200 hover:border-[hsl(var(--primary))]"
            }`}
          >
            {p === "FLPP" ? "FLPP (Subsidi)" : "Komersial"}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between mb-2">
            <Label className="text-sm text-slate-600">Uang Muka (DP)</Label>
            <span className="text-sm font-semibold text-[hsl(var(--primary))]">{dp}% · {rupiah(price * dp / 100)}</span>
          </div>
          <Slider data-testid="sim-dp-slider" value={[dp]} min={0} max={50} step={1} onValueChange={(v) => setDp(v[0])} />
        </div>
        <div>
          <div className="flex justify-between mb-2">
            <Label className="text-sm text-slate-600">Tenor</Label>
            <span className="text-sm font-semibold text-[hsl(var(--primary))]">{tenor} tahun</span>
          </div>
          <Slider data-testid="sim-tenor-slider" value={[tenor]} min={5} max={30} step={1} onValueChange={(v) => setTenor(v[0])} />
        </div>
      </div>

      {result && (
        <div className="mt-5 pt-4 border-t border-slate-100">
          <p className="text-xs text-slate-500 mb-1">Estimasi angsuran per bulan</p>
          <p data-testid="sim-first-installment" className="font-heading text-3xl font-bold text-[hsl(var(--primary))]">
            {rupiah(result.first_installment)}
          </p>
          <div className="mt-3 space-y-1.5">
            {result.schedule.map((s, i) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-slate-500">
                  {s.phase} · thn {s.from_year}-{s.to_year} · {s.rate}%
                </span>
                <span className="font-medium text-slate-700">{rupiah(s.monthly)}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-3">
            Plafon KPR {rupiah(result.loan_amount)} · {result.program_label}
          </p>

          <div className="mt-4 flex flex-col sm:flex-row gap-2">
            <Button
              data-testid="sim-toggle-amortization"
              variant="outline"
              size="sm"
              onClick={toggleAmort}
              disabled={loadingAmort}
              className="flex-1"
            >
              {loadingAmort ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Table2 className="h-4 w-4 mr-1.5" />}
              {showAmort ? "Sembunyikan Amortisasi" : "Tabel Amortisasi"}
            </Button>
            <Button
              data-testid="sim-download-pdf"
              size="sm"
              onClick={downloadPdf}
              disabled={downloading}
              className="flex-1 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90"
            >
              {downloading ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Download className="h-4 w-4 mr-1.5" />}
              Unduh PDF
            </Button>
          </div>
          {user && user.role === "consumer" && (
            <Button
              data-testid="sim-save"
              variant="outline"
              size="sm"
              onClick={saveSim}
              disabled={saving}
              className="w-full mt-2 border-[hsl(var(--primary))] text-[hsl(var(--primary))] hover:bg-[hsl(var(--secondary))]"
            >
              {saving ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />}
              Simpan ke Riwayat
            </Button>
          )}

          {showAmort && amort && (
            <div data-testid="sim-amortization-table" className="mt-4">
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="rounded-lg bg-slate-50 border border-slate-100 p-2.5">
                  <p className="text-[11px] text-slate-500">Total bunga (estimasi)</p>
                  <p className="text-sm font-semibold text-slate-800">{rupiah(amort.total_interest)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 border border-slate-100 p-2.5">
                  <p className="text-[11px] text-slate-500">Total pembayaran</p>
                  <p className="text-sm font-semibold text-slate-800">{rupiah(amort.total_paid)}</p>
                </div>
              </div>
              <p className="text-xs text-slate-500 mb-2">Rincian angsuran bulan per bulan (pokok & bunga)</p>
              <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-200">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-[hsl(var(--secondary))] text-slate-700">
                    <tr>
                      <th className="text-left font-semibold px-2 py-2">Bln</th>
                      <th className="text-right font-semibold px-2 py-2">Angsuran</th>
                      <th className="text-right font-semibold px-2 py-2">Pokok</th>
                      <th className="text-right font-semibold px-2 py-2">Bunga</th>
                      <th className="text-right font-semibold px-2 py-2">Sisa Pokok</th>
                    </tr>
                  </thead>
                  <tbody>
                    {amort.months.map((m) => (
                      <tr
                        key={m.month}
                        className={`border-t border-slate-100 ${m.month % 12 === 1 ? "bg-amber-50/40" : ""}`}
                      >
                        <td className="px-2 py-1.5 text-slate-600">{m.month}</td>
                        <td className="px-2 py-1.5 text-right text-slate-700">{rupiah(m.installment)}</td>
                        <td className="px-2 py-1.5 text-right text-emerald-700">{rupiah(m.principal)}</td>
                        <td className="px-2 py-1.5 text-right text-orange-700">{rupiah(m.interest)}</td>
                        <td className="px-2 py-1.5 text-right text-slate-500">{rupiah(m.balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
