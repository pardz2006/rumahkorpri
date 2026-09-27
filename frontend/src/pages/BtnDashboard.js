import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Navbar } from "../components/Navbar";
import { StatCard, StatusBadge } from "../components/shared";
import { api, rupiah, BACKEND, formatApiErrorDetail } from "../lib/api";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "../components/ui/dialog";
import { Landmark, Clock, CheckCircle2, FileDown, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const DECISIONS = [
  { k: "pre_approved", t: "Pra-Disetujui", c: "bg-teal-600" },
  { k: "approved", t: "Disetujui", c: "bg-emerald-600" },
  { k: "need_revision", t: "Perlu Revisi", c: "bg-orange-500" },
  { k: "rejected", t: "Ditolak", c: "bg-red-600" },
];

export default function BtnDashboard() {
  const { user } = useAuth();
  const [apps, setApps] = useState([]);
  const [decideFor, setDecideFor] = useState(null);
  const [decision, setDecision] = useState("pre_approved");
  const [evaluatorNote, setEvaluatorNote] = useState("");
  const [slikNote, setSlikNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.get("/kpr/applications").then((r) => setApps(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const submit = async () => {
    setBusy(true);
    try {
      await api.patch(`/kpr/applications/${decideFor.id}`, {
        status: decision, evaluator_note: evaluatorNote || null, slik_note: slikNote || null,
      });
      toast.success("Keputusan kelayakan KPR tersimpan & notifikasi terkirim.");
      setDecideFor(null); setEvaluatorNote(""); setSlikNote(""); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const pending = apps.filter((a) => a.status === "pending").length;
  const approved = apps.filter((a) => a.status === "approved").length;

  return (
    <div className="App">
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <h1 className="font-heading text-3xl font-bold text-slate-800">Dashboard Analis {user?.bank || "Bank"}</h1>
        <p className="text-slate-500 mt-1">Penilaian kelayakan & scoring KPR (SLIK OJK / Scoring Internal).</p>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
          <StatCard label="Total Pengajuan" value={apps.length} icon={Landmark} />
          <StatCard label="Menunggu Review" value={pending} icon={Clock} accent="bg-amber-100" />
          <StatCard label="Disetujui" value={approved} icon={CheckCircle2} accent="bg-emerald-100" />
          <StatCard label="Tingkat Approval" value={apps.length ? Math.round((approved / apps.length) * 100) + "%" : "0%"} icon={ShieldCheck} />
        </div>

        <div className="mt-8 space-y-4">
          {apps.length === 0 && <p className="text-slate-400 text-center py-10">Belum ada pengajuan KPR diteruskan.</p>}
          {apps.map((a) => (
            <div key={a.id} data-testid={`kpr-app-${a.id}`} className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-heading text-lg font-semibold text-slate-800">{a.booking?.consumer?.name}</h3>
                    <StatusBadge status={a.status} />
                  </div>
                  <p className="text-sm text-slate-500 mt-1">
                    {a.booking?.consumer?.instansi} · NIK {a.booking?.consumer?.nik || "-"} · {a.booking?.consumer?.phone}
                  </p>
                  <div className="grid sm:grid-cols-3 gap-x-6 gap-y-1 mt-3 text-sm">
                    <p className="text-slate-500">Unit: <span className="text-slate-700 font-medium">{a.booking?.unit?.type}</span></p>
                    <p className="text-slate-500">Plafon: <span className="text-slate-700 font-medium">{rupiah(a.loan_amount)}</span></p>
                    <p className="text-slate-500">Program: <span className="text-slate-700 font-medium">{a.program}</span></p>
                    <p className="text-slate-500">Penghasilan: <span className="text-slate-700 font-medium">{rupiah(a.booking?.consumer?.monthly_income)}</span></p>
                    <p className="text-slate-500">Angsuran: <span className="text-slate-700 font-medium">{rupiah(a.booking?.kpr_sim?.first_installment)}/bln</span></p>
                    <p className="text-slate-500">Tenor: <span className="text-slate-700 font-medium">{a.booking?.tenor_years} thn</span></p>
                  </div>
                  {a.evaluator_note && <p className="text-sm text-slate-600 mt-2 bg-[hsl(var(--muted))]/60 rounded p-2">📝 {a.evaluator_note}</p>}
                </div>
                <div className="flex flex-col gap-2">
                  <Button asChild variant="outline" size="sm" data-testid={`btn-spr-${a.id}`}>
                    <a href={`${BACKEND}/api/bookings/${a.booking_id}/spr.pdf`} target="_blank" rel="noreferrer">
                      <FileDown className="h-4 w-4 mr-1.5" /> Lihat SPR
                    </a>
                  </Button>
                  <Button size="sm" onClick={() => { setDecideFor(a); setDecision("pre_approved"); }}
                    data-testid={`decide-open-${a.id}`}
                    className="bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
                    Ambil Keputusan
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Dialog open={!!decideFor} onOpenChange={(o) => !o && setDecideFor(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Keputusan Kelayakan KPR</DialogTitle>
            <DialogDescription>{decideFor?.booking?.consumer?.name} · Plafon {rupiah(decideFor?.loan_amount)}</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-2">
            {DECISIONS.map((d) => (
              <button key={d.k} onClick={() => setDecision(d.k)} data-testid={`decision-${d.k}`}
                className={`text-sm font-medium rounded-lg py-2.5 text-white transition-opacity ${d.c} ${decision === d.k ? "opacity-100 ring-2 ring-offset-2 ring-slate-300" : "opacity-50 hover:opacity-80"}`}>
                {d.t}
              </button>
            ))}
          </div>
          <div className="space-y-3 mt-2">
            <div>
              <p className="text-sm text-slate-600 mb-1">Catatan SLIK / Scoring</p>
              <Textarea value={slikNote} onChange={(e) => setSlikNote(e.target.value)} placeholder="mis. Skor kredit Kol-1, DBR 32%..." data-testid="slik-note" />
            </div>
            <div>
              <p className="text-sm text-slate-600 mb-1">Catatan untuk Peminat</p>
              <Textarea value={evaluatorNote} onChange={(e) => setEvaluatorNote(e.target.value)} placeholder="mis. Lengkapi slip gaji 3 bulan terakhir..." data-testid="evaluator-note" />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={submit} disabled={busy} data-testid="submit-decision-btn"
              className="w-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
              {busy ? "Menyimpan..." : "Simpan Keputusan"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
