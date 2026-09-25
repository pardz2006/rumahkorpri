import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { Navbar } from "../components/Navbar";
import { StatusBadge, fileToDataUrl } from "../components/shared";
import { api, rupiah, BACKEND, formatApiErrorDetail } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { useAuth } from "../context/AuthContext";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "../components/ui/dialog";
import {
  Home, QrCode, CreditCard, FileDown, Upload, CheckCircle2, Clock, FileText, Wallet, CircleDollarSign,
  MapPin, Calculator, Trash2, GitCompare, Share2,
} from "lucide-react";

export default function ConsumerPortal() {
  const loc = useLocation();
  const { user, setUser } = useAuth();
  const [bookings, setBookings] = useState([]);
  const [payFor, setPayFor] = useState(null);
  const [payInfo, setPayInfo] = useState(null);
  const [payKind, setPayKind] = useState("booking_fee");
  const [payTermin, setPayTermin] = useState(null);
  const [sims, setSims] = useState([]);
  const [compareIds, setCompareIds] = useState([]);
  const [profile, setProfile] = useState({ city: "", province: "", phone: "" });
  const [savingProfile, setSavingProfile] = useState(false);

  const load = () => {
    api.get("/bookings").then((r) => setBookings(r.data)).catch(() => {});
    api.get("/simulations").then((r) => setSims(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (user) setProfile({ city: user.city || "", province: user.province || "", phone: user.phone || "" });
  }, [user]);

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      const { data } = await api.patch("/profile", profile);
      setUser(data);
      toast.success("Profil domisili diperbarui — urutan proyek menyesuaikan domisili Anda");
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    } finally {
      setSavingProfile(false);
    }
  };

  const deleteSim = async (id) => {
    try {
      await api.delete(`/simulations/${id}`);
      setCompareIds((ids) => ids.filter((x) => x !== id));
      toast.success("Simulasi dihapus");
      load();
    } catch (e) { toast.error("Gagal menghapus simulasi"); }
  };

  const toggleCompare = (id) => {
    setCompareIds((ids) => ids.includes(id) ? ids.filter((x) => x !== id)
      : (ids.length >= 3 ? (toast.info("Maksimal 3 simulasi dibandingkan"), ids) : [...ids, id]));
  };

  const shareSim = async (s) => {
    try {
      const { data } = await api.post(`/simulations/${s.id}/share`);
      const url = `${window.location.origin}${data.path}`;
      const text = `Simulasi KPR "${s.label}" — angsuran ± ${rupiah(s.first_installment)}/bln. Lihat detail: ${url}`;
      try {
        await navigator.clipboard.writeText(url);
        toast.success("Tautan disalin ke clipboard");
      } catch (_) { /* clipboard optional */ }
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank");
    } catch (e) { toast.error("Gagal membuat tautan bagikan"); }
  };

  const compareSims = sims.filter((s) => compareIds.includes(s.id));

  const downloadSimPdf = async (s) => {
    try {
      const res = await api.post("/kpr/simulate/pdf", {
        price: s.price, dp_percent: s.dp_percent, tenor_years: s.tenor_years, program: s.program,
      }, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `simulasi-kpr-${s.program.toLowerCase()}-${s.tenor_years}thn.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("PDF simulasi diunduh");
    } catch (e) { toast.error("Gagal mengunduh PDF"); }
  };

  useEffect(() => {
    if (loc.state?.openBooking) {
      api.get(`/bookings/${loc.state.openBooking}`).then((r) => openPay(r.data, "booking_fee")).catch(() => {});
    }
  }, [loc.state]);

  const openPay = async (b, kind, terminNo) => {
    setPayFor(b); setPayKind(kind); setPayTermin(terminNo ?? null);
    if (kind === "dp_termin") {
      const { data } = await api.post(`/bookings/${b.id}/pay-dp`, null, { params: { termin_no: terminNo } });
      setPayInfo(data);
    } else {
      const { data } = await api.post(`/bookings/${b.id}/pay`);
      setPayInfo(data);
    }
  };

  const confirmPay = async () => {
    try {
      await api.post("/payments/webhook", {
        booking_id: payFor.id, status: "paid", kind: payKind, termin_no: payTermin,
      });
      toast.success(payKind === "dp_termin"
        ? `Pembayaran termin ke-${payTermin} terverifikasi!`
        : "Pembayaran terverifikasi! SPR sedang diproses developer.");
      setPayFor(null); setPayInfo(null); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const uploadDoc = async (bookingId, docType, file) => {
    const dataUrl = await fileToDataUrl(file);
    try {
      await api.post(`/bookings/${bookingId}/documents`, { doc_type: docType, file_data: dataUrl, file_name: file.name });
      toast.success(`${docType} berhasil diunggah`);
      load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  return (
    <div className="App">
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <h1 className="font-heading text-3xl font-bold text-slate-800">Portal Pemesanan Saya</h1>
        <p className="text-slate-500 mt-1">Pantau pembayaran, SPR, dan kelengkapan dokumen KPR Anda.</p>

        {/* Profil domisili */}
        <div data-testid="profile-domicile-card" className="mt-6 bg-white rounded-xl border border-slate-200/80 shadow-sm p-5 sm:p-6">
          <div className="flex items-center gap-2 mb-4">
            <MapPin className="h-5 w-5 text-[hsl(var(--primary))]" />
            <div>
              <p className="font-heading font-semibold text-slate-800">Profil Domisili</p>
              <p className="text-xs text-slate-500">Proyek perumahan diurutkan sesuai kota lalu provinsi Anda.</p>
            </div>
          </div>
          <div className="grid sm:grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label className="text-sm text-slate-600">Kota / Kabupaten</Label>
              <Input data-testid="profile-city" value={profile.city} onChange={(e) => setProfile({ ...profile, city: e.target.value })} placeholder="mis. Bekasi" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-sm text-slate-600">Provinsi</Label>
              <Input data-testid="profile-province" value={profile.province} onChange={(e) => setProfile({ ...profile, province: e.target.value })} placeholder="mis. Jawa Barat" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-sm text-slate-600">No. WhatsApp</Label>
              <Input data-testid="profile-phone" value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} placeholder="08xxxxxxxxxx" />
            </div>
          </div>
          <Button data-testid="profile-save" onClick={saveProfile} disabled={savingProfile} className="mt-4 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
            {savingProfile ? "Menyimpan..." : "Simpan Profil"}
          </Button>
        </div>

        <Tabs defaultValue="pesanan" className="mt-8">
          <TabsList>
            <TabsTrigger value="pesanan" data-testid="tab-pesanan">Pemesanan Saya</TabsTrigger>
            <TabsTrigger value="riwayat" data-testid="tab-riwayat">Riwayat Simulasi{sims.length ? ` (${sims.length})` : ""}</TabsTrigger>
          </TabsList>

          <TabsContent value="pesanan" className="mt-5">
        {bookings.length === 0 && (
          <div className="mt-10 bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center">
            <Home className="h-10 w-10 text-slate-300 mx-auto" />
            <p className="text-slate-500 mt-3">Belum ada pemesanan. Jelajahi proyek perumahan untuk memesan unit.</p>
            <Button className="mt-4 bg-[hsl(var(--primary))]" onClick={() => (window.location.href = "/")}>Lihat Proyek</Button>
          </div>
        )}

        <div className="mt-8 space-y-6">
          {bookings.map((b) => (
            <div key={b.id} data-testid={`booking-${b.id}`} className="bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
              <div className="p-5 sm:p-6 flex flex-wrap items-start justify-between gap-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-heading text-xl font-semibold text-slate-800">{b.unit?.type}</h3>
                    <StatusBadge status={b.payment_status} />
                    {b.spr_status !== "not_ready" && <StatusBadge status={b.spr_status} />}
                  </div>
                  <p className="text-sm text-slate-500 mt-1">
                    {b.project?.name} · Blok {b.unit?.block}/{b.unit?.number} · {rupiah(b.unit?.price)}
                  </p>
                  <p className="text-sm text-slate-500 mt-0.5">
                    Angsuran ± {rupiah(b.kpr_sim?.first_installment)}/bln · {b.program} · {b.tenor_years} thn
                  </p>
                  {b.spr_status === "issued" && (
                    <p className="text-sm mt-1 flex items-center gap-1.5">
                      <Wallet className="h-4 w-4 text-[hsl(var(--primary))]" />
                      <span className="text-slate-500">Uang Muka (DP {b.dp_percent}%): </span>
                      <span className="font-semibold text-slate-700">{rupiah(b.dp_amount)}</span>
                      <StatusBadge status={b.dp_payment_status === "paid" ? "paid" : (b.dp_payment_status === "partial" ? "uploaded" : "pending")} />
                    </p>
                  )}
                </div>
                <div className="flex flex-col gap-2">
                  {b.payment_status === "pending" && (
                    <Button onClick={() => openPay(b, "booking_fee")} data-testid={`pay-btn-${b.id}`} className="bg-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/90">
                      Bayar Booking Fee
                    </Button>
                  )}
                  {b.spr_status === "issued" && (
                    <Button asChild variant="outline" data-testid={`spr-download-${b.id}`}>
                      <a href={`${BACKEND}/api/bookings/${b.id}/spr.pdf`} target="_blank" rel="noreferrer">
                        <FileDown className="h-4 w-4 mr-1.5" /> Unduh SPR
                      </a>
                    </Button>
                  )}
                </div>
              </div>

              {/* DP termin schedule */}
              {b.spr_status === "issued" && b.dp_termins && (
                <div className="px-5 sm:px-6 pt-5 border-b border-slate-100 pb-5">
                  <div className="flex items-center justify-between mb-3">
                    <p className="font-semibold text-slate-700 flex items-center gap-2">
                      <CircleDollarSign className="h-4 w-4 text-[hsl(var(--primary))]" /> Jadwal Cicilan Uang Muka (DP)
                    </p>
                    <p className="text-sm text-slate-500">
                      Terbayar <span className="font-semibold text-emerald-600">{rupiah(b.dp_paid_amount || 0)}</span>
                      {" · "}Sisa <span className="font-semibold text-[hsl(var(--accent))]">{rupiah((b.dp_amount || 0) - (b.dp_paid_amount || 0))}</span>
                    </p>
                  </div>
                  <div className="grid sm:grid-cols-3 gap-3">
                    {b.dp_termins.map((t) => {
                      const prevUnpaid = b.dp_termins.some((x) => x.no < t.no && x.status !== "paid");
                      const payable = t.status !== "paid" && !prevUnpaid;
                      return (
                        <div key={t.no} data-testid={`dp-termin-${b.id}-${t.no}`}
                          className={`rounded-lg border p-3 ${t.status === "paid" ? "border-emerald-200 bg-emerald-50/60" : "border-slate-200 bg-[hsl(var(--muted))]/40"}`}>
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-500">Termin {t.no}</span>
                            <StatusBadge status={t.status === "paid" ? "paid" : "pending"} />
                          </div>
                          <p className="font-heading text-lg font-bold text-slate-800 mt-1">{rupiah(t.amount)}</p>
                          {t.status === "paid" ? (
                            <p className="text-[11px] text-emerald-600 mt-1 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Lunas · {t.ref}</p>
                          ) : (
                            <Button size="sm" disabled={!payable} onClick={() => openPay(b, "dp_termin", t.no)}
                              data-testid={`pay-dp-termin-${b.id}-${t.no}`}
                              className="w-full mt-2 h-8 bg-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/90 disabled:opacity-40">
                              {payable ? "Bayar Termin" : "Menunggu termin sebelumnya"}
                            </Button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Documents checklist */}
              {b.spr_status === "issued" && (
                <div className="p-5 sm:p-6">
                  <p className="font-semibold text-slate-700 flex items-center gap-2 mb-3">
                    <FileText className="h-4 w-4 text-[hsl(var(--primary))]" /> Kelengkapan Dokumen KPR
                  </p>
                  <div className="grid sm:grid-cols-2 gap-2">
                    {b.documents.map((d) => (
                      <div key={d.id} data-testid={`doc-${d.id}`} className="flex items-center justify-between bg-[hsl(var(--muted))]/50 rounded-lg px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          {d.status === "valid" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Clock className="h-4 w-4 text-slate-400" />}
                          <div>
                            <p className="text-sm font-medium text-slate-700">{d.doc_type}</p>
                            {d.file_name && <p className="text-[11px] text-slate-400 truncate max-w-[140px]">{d.file_name}</p>}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusBadge status={d.status} />
                          <label className="cursor-pointer">
                            <input type="file" className="hidden" data-testid={`upload-${d.id}`}
                              onChange={(e) => e.target.files[0] && uploadDoc(b.id, d.doc_type, e.target.files[0])} />
                            <span className="inline-flex items-center h-8 w-8 justify-center rounded-lg hover:bg-slate-200 text-slate-500">
                              <Upload className="h-4 w-4" />
                            </span>
                          </label>
                        </div>
                      </div>
                    ))}
                  </div>
                  {b.documents.some((d) => d.note) && (
                    <div className="mt-3 space-y-1">
                      {b.documents.filter((d) => d.note).map((d) => (
                        <p key={d.id} className="text-xs text-orange-600">• {d.doc_type}: {d.note}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
          </TabsContent>

          <TabsContent value="riwayat" className="mt-5">
            {sims.length === 0 && (
              <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center">
                <Calculator className="h-10 w-10 text-slate-300 mx-auto" />
                <p className="text-slate-500 mt-3">Belum ada simulasi tersimpan. Buka detail unit lalu klik "Simpan ke Riwayat" pada simulator KPR.</p>
              </div>
            )}
            {compareSims.length >= 2 && (
              <div data-testid="sim-compare-panel" className="mb-5 bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-x-auto">
                <div className="flex items-center gap-2 p-4 border-b border-slate-100">
                  <GitCompare className="h-4 w-4 text-[hsl(var(--primary))]" />
                  <p className="font-semibold text-slate-700">Perbandingan {compareSims.length} Simulasi</p>
                </div>
                <table className="w-full text-sm min-w-[520px]">
                  <tbody className="divide-y divide-slate-100">
                    <CompareRow label="Program" values={compareSims.map((s) => s.program_label)} />
                    <CompareRow label="Harga" values={compareSims.map((s) => rupiah(s.price))} />
                    <CompareRow label="DP" values={compareSims.map((s) => `${s.dp_percent}% · ${rupiah(s.dp_amount)}`)} />
                    <CompareRow label="Plafon KPR" values={compareSims.map((s) => rupiah(s.loan_amount))} />
                    <CompareRow label="Tenor" values={compareSims.map((s) => `${s.tenor_years} thn`)} />
                    <CompareRow label="Angsuran awal" values={compareSims.map((s) => rupiah(s.first_installment))} highlight />
                    <CompareRow label="Total bunga" values={compareSims.map((s) => rupiah(s.total_interest))} />
                    <CompareRow label="Total bayar" values={compareSims.map((s) => rupiah(s.total_paid))} />
                  </tbody>
                </table>
              </div>
            )}
            <div className="space-y-3">
              {sims.map((s) => (
                <div key={s.id} data-testid={`sim-item-${s.id}`} className="bg-white rounded-xl border border-slate-200/80 shadow-sm p-4 flex items-center gap-4">
                  <input type="checkbox" data-testid={`sim-compare-${s.id}`} checked={compareIds.includes(s.id)} onChange={() => toggleCompare(s.id)} className="h-4 w-4 accent-[hsl(var(--primary))]" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 truncate">{s.label}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{s.program_label} · DP {s.dp_percent}% · {s.tenor_years} thn · {new Date(s.created_at).toLocaleDateString("id-ID")}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-slate-400">Angsuran awal</p>
                    <p className="font-heading font-bold text-[hsl(var(--primary))]">{rupiah(s.first_installment)}</p>
                  </div>
                  <button data-testid={`sim-share-${s.id}`} onClick={() => shareSim(s)} title="Bagikan"
                    className="h-9 w-9 grid place-items-center rounded-lg text-slate-400 hover:bg-[hsl(var(--secondary))] hover:text-[hsl(var(--primary))] shrink-0">
                    <Share2 className="h-4 w-4" />
                  </button>
                  <button data-testid={`sim-pdf-${s.id}`} onClick={() => downloadSimPdf(s)} title="Unduh PDF"
                    className="h-9 w-9 grid place-items-center rounded-lg text-slate-400 hover:bg-[hsl(var(--secondary))] hover:text-[hsl(var(--primary))] shrink-0">
                    <FileDown className="h-4 w-4" />
                  </button>
                  <button data-testid={`sim-delete-${s.id}`} onClick={() => deleteSim(s.id)} className="h-9 w-9 grid place-items-center rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-600 shrink-0">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Payment dialog */}
      <Dialog open={!!payFor} onOpenChange={(o) => { if (!o) { setPayFor(null); setPayInfo(null); } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{payKind === "dp_termin" ? `Pembayaran DP Termin ${payTermin}` : "Pembayaran Booking Fee"}</DialogTitle>
            <DialogDescription>{payFor?.unit?.type} · {rupiah(payInfo?.amount)}</DialogDescription>
          </DialogHeader>
          {payInfo && (
            <div className="text-center py-2">
              {payInfo.method === "QRIS" ? (
                <>
                  <div className="mx-auto h-44 w-44 bg-white border-2 border-slate-200 rounded-xl grid place-items-center">
                    <QrCode className="h-32 w-32 text-slate-800" />
                  </div>
                  <p className="text-sm text-slate-500 mt-3">Pindai QRIS untuk membayar</p>
                </>
              ) : (
                <div className="bg-[hsl(var(--secondary))]/40 rounded-xl p-5">
                  <CreditCard className="h-8 w-8 text-[hsl(var(--primary))] mx-auto" />
                  <p className="text-sm text-slate-500 mt-2">Virtual Account BTN</p>
                  <p className="font-heading text-2xl font-bold text-slate-800 tracking-wider mt-1" data-testid="va-number">{payInfo.va_number}</p>
                </div>
              )}
              <p className="text-xs text-slate-400 mt-4">Simulasi — tekan tombol di bawah untuk memicu verifikasi otomatis.</p>
            </div>
          )}
          <Button onClick={confirmPay} data-testid="confirm-payment-btn" className="w-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
            Saya Sudah Bayar (Konfirmasi)
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CompareRow({ label, values, highlight }) {
  return (
    <tr className={highlight ? "bg-[hsl(var(--secondary))]/40" : ""}>
      <td className="px-4 py-2.5 text-slate-500 font-medium whitespace-nowrap">{label}</td>
      {values.map((v, i) => (
        <td key={i} className={`px-4 py-2.5 text-right ${highlight ? "font-bold text-[hsl(var(--primary))]" : "text-slate-700"}`}>{v}</td>
      ))}
    </tr>
  );
}
