import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Navbar } from "../components/Navbar";
import { StatCard, StatusBadge } from "../components/shared";
import { api, rupiah, BACKEND, formatApiErrorDetail } from "../lib/api";
import { Button } from "../components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "../components/ui/dialog";
import { Textarea } from "../components/ui/textarea";
import { Input } from "../components/ui/input";
import {
  Users, FileCheck, MessageSquare, AlertTriangle, Send, FileText, Eye, CheckCircle2, XCircle,
} from "lucide-react";

export default function KorpriDashboard() {
  const [stats, setStats] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [waLogs, setWaLogs] = useState([]);
  const [waEnabled, setWaEnabled] = useState(false);
  const [testPhone, setTestPhone] = useState("");
  const [testing, setTesting] = useState(false);
  const [detail, setDetail] = useState(null);

  const load = () => {
    api.get("/stats").then((r) => setStats(r.data)).catch(() => {});
    api.get("/bookings").then((r) => setBookings(r.data)).catch(() => {});
    api.get("/wa-logs").then((r) => setWaLogs(r.data)).catch(() => {});
    api.get("/whatsapp/status").then((r) => setWaEnabled(r.data.enabled)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const sendFollowup = async (b) => {
    try {
      const { data } = await api.post(`/bookings/${b.id}/followup`);
      if (data.channel === "twilio" && data.wa_status === "sent") {
        toast.success(`Pesan WhatsApp terkirim via Twilio ke ${b.consumer?.phone}`);
      } else if (data.channel === "twilio") {
        toast.error(`WhatsApp gagal terkirim: ${data.wa_error || "cek konfigurasi Twilio"}`);
      } else {
        toast.success(`Pengingat tersimpan (simulasi): ${data.missing.join(", ")}`);
      }
      load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const sendTest = async () => {
    if (!testPhone.trim()) { toast.error("Isi nomor tujuan lebih dulu"); return; }
    setTesting(true);
    try {
      const { data } = await api.post("/whatsapp/test", { phone: testPhone.trim() });
      if (data.status === "sent") toast.success(`Terkirim ke ${testPhone} (SID ${data.sid?.slice(0, 10)}…)`);
      else toast.error(`Gagal: ${data.error || "cek nomor & join sandbox"}`);
      load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setTesting(false); }
  };

  const verifyDoc = async (docId, status) => {
    const note = status === "invalid" ? window.prompt("Catatan (opsional):") || null : null;
    try {
      await api.patch(`/documents/${docId}/verify`, { status, note });
      toast.success("Status dokumen diperbarui");
      const fresh = await api.get(`/bookings/${detail.id}`);
      setDetail(fresh.data); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const withSpr = bookings.filter((b) => b.spr_status === "issued");

  return (
    <div className="App">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <h1 className="font-heading text-3xl font-bold text-slate-800">Dashboard CRM Rumah KORPRI</h1>
        <p className="text-slate-500 mt-1">Pantau pemesanan, kelengkapan dokumen, dan otomasi follow-up.</p>

        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
            <StatCard label="Total Pemesanan" value={stats.total_bookings} icon={Users} />
            <StatCard label="Pembayaran Lunas" value={stats.paid_bookings} icon={FileCheck} />
            <StatCard label="SPR Terbit" value={stats.spr_issued} icon={FileText} />
            <StatCard label="Dokumen Kurang" value={stats.docs_missing} icon={AlertTriangle} accent="bg-orange-100" />
          </div>
        )}

        <Tabs defaultValue="berkas" className="mt-8">
          <TabsList>
            <TabsTrigger value="berkas" data-testid="tab-berkas">Checklist Dokumen</TabsTrigger>
            <TabsTrigger value="wa" data-testid="tab-wa">Log WhatsApp</TabsTrigger>
          </TabsList>

          <TabsContent value="berkas" className="mt-5">
            <div className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-[hsl(var(--muted))]/60 text-slate-500 text-left">
                  <tr>
                    <th className="px-5 py-3 font-medium">Peminat</th>
                    <th className="px-5 py-3 font-medium">Unit</th>
                    <th className="px-5 py-3 font-medium">Kelengkapan</th>
                    <th className="px-5 py-3 font-medium text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {withSpr.length === 0 && <tr><td colSpan={4} className="px-5 py-10 text-center text-slate-400">Belum ada berkas SPR terbit.</td></tr>}
                  {withSpr.map((b) => {
                    const total = b.documents.length;
                    const valid = b.documents.filter((d) => d.status === "valid").length;
                    const missing = b.documents.filter((d) => ["missing", "invalid"].includes(d.status)).length;
                    return (
                      <tr key={b.id} data-testid={`crm-row-${b.id}`}>
                        <td className="px-5 py-3">
                          <p className="font-medium text-slate-800">{b.consumer?.name}</p>
                          <p className="text-xs text-slate-400">{b.consumer?.instansi} · {b.consumer?.phone}</p>
                        </td>
                        <td className="px-5 py-3 text-slate-600">{b.unit?.type}<br /><span className="text-xs text-slate-400">{b.project?.name}</span></td>
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-2">
                            <div className="h-2 w-24 rounded-full bg-slate-100 overflow-hidden">
                              <div className="h-full bg-[hsl(var(--primary))]" style={{ width: `${total ? (valid / total) * 100 : 0}%` }} />
                            </div>
                            <span className="text-xs text-slate-500">{valid}/{total} valid</span>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="outline" onClick={() => setDetail(b)} data-testid={`crm-view-${b.id}`}>
                              <Eye className="h-4 w-4 mr-1" /> Berkas
                            </Button>
                            <Button size="sm" disabled={missing === 0} onClick={() => sendFollowup(b)} data-testid={`crm-followup-${b.id}`}
                              className="bg-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/90 disabled:opacity-40">
                              <Send className="h-4 w-4 mr-1" /> Follow-Up WA
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="wa" className="mt-5">
            <div className="mb-4 flex items-center gap-2" data-testid="wa-channel-status">
              {waEnabled ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> WhatsApp aktif via Twilio
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Mode simulasi — kredensial Twilio belum diisi
                </span>
              )}
            </div>
            {waEnabled && (
              <div data-testid="wa-test-box" className="mb-5 bg-white rounded-xl border border-slate-200/80 shadow-sm p-4">
                <p className="text-sm font-semibold text-slate-700">Tes Kirim WhatsApp</p>
                <p className="text-xs text-slate-500 mt-0.5 mb-3">
                  Akun trial: penerima wajib gabung sandbox dulu — kirim <b>join &lt;kode&gt;</b> ke +1 415 523 8886 dari WhatsApp Anda.
                </p>
                <div className="flex gap-2">
                  <Input data-testid="wa-test-phone" value={testPhone} onChange={(e) => setTestPhone(e.target.value)} placeholder="+62812xxxxxxx" className="max-w-xs" />
                  <Button data-testid="wa-test-send" onClick={sendTest} disabled={testing} className="bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
                    {testing ? "Mengirim..." : "Kirim Tes"}
                  </Button>
                </div>
              </div>
            )}
            <div className="space-y-3">
              {waLogs.length === 0 && <p className="text-slate-400 text-center py-10">Belum ada log pesan.</p>}
              {waLogs.map((w) => (
                <div key={w.id} data-testid={`wa-log-${w.id}`} className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-sm flex gap-3">
                  <div className="h-9 w-9 rounded-full bg-green-100 grid place-items-center shrink-0">
                    <MessageSquare className="h-4 w-4 text-green-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-slate-800 text-sm">{w.recipient_name} · {w.phone}</p>
                      <span className="text-xs text-slate-400">{new Date(w.sent_at).toLocaleString("id-ID")}</span>
                    </div>
                    <p className="text-sm text-slate-600 mt-1 whitespace-pre-line">{w.message}</p>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-500">template: {w.template}</span>
                      <span className={`text-[11px] px-2 py-0.5 rounded ${
                        w.status === "sent" ? "bg-emerald-100 text-emerald-700"
                        : w.status === "failed" ? "bg-red-100 text-red-700"
                        : "bg-amber-100 text-amber-700"
                      }`}>
                        {w.channel === "twilio" ? (w.status === "sent" ? "terkirim · Twilio" : `gagal · ${w.error || "Twilio"}`) : "simulasi"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Berkas detail dialog */}
      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Verifikasi Berkas — {detail?.consumer?.name}</DialogTitle>
            <DialogDescription>{detail?.unit?.type} · {detail?.project?.name}</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 max-h-[60vh] overflow-y-auto">
            {detail?.documents.map((d) => (
              <div key={d.id} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2.5">
                <div>
                  <p className="text-sm font-medium text-slate-700">{d.doc_type}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <StatusBadge status={d.status} />
                    {d.file_data && (
                      <a href={d.file_data} target="_blank" rel="noreferrer" className="text-xs text-[hsl(var(--primary))] hover:underline">Lihat file</a>
                    )}
                  </div>
                </div>
                {d.status !== "missing" && (
                  <div className="flex gap-1.5">
                    <button onClick={() => verifyDoc(d.id, "valid")} data-testid={`verify-valid-${d.id}`}
                      className="h-8 w-8 grid place-items-center rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-600">
                      <CheckCircle2 className="h-4 w-4" />
                    </button>
                    <button onClick={() => verifyDoc(d.id, "invalid")} data-testid={`verify-invalid-${d.id}`}
                      className="h-8 w-8 grid place-items-center rounded-lg bg-red-50 hover:bg-red-100 text-red-600">
                      <XCircle className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
