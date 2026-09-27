import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Navbar } from "../components/Navbar";
import { KprSimulator } from "../components/KprSimulator";
import { StatusBadge } from "../components/shared";
import { ZoomableImage } from "../components/ZoomableImage";
import { UnitGallery } from "../components/UnitGallery";
import { BlockPlan } from "../components/BlockPlan";
import { VideoGallery } from "../components/VideoGallery";
import { api, rupiah, formatApiErrorDetail, mediaUrl } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import { Slider } from "../components/ui/slider";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "../components/ui/dialog";
import { MapPin, MapPinned, Home, Maximize, ArrowLeft, QrCode, CreditCard, Navigation, Route } from "lucide-react";

export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [selected, setSelected] = useState(null);
  const [unitDetail, setUnitDetail] = useState(null);
  const [bookingCfg, setBookingCfg] = useState({ program: "FLPP", dp_percent: 10, tenor_years: 15, payment_method: "QRIS" });
  const [busy, setBusy] = useState(false);

  const load = () => api.get(`/projects/${id}`).then((r) => { setProject(r.data); setBookingCfg((c) => ({ ...c, program: r.data.program })); });
  useEffect(() => { load(); }, [id]);

  const openBooking = (unit) => {
    if (!user) { toast.info("Silakan masuk sebagai Peminat untuk memesan"); navigate("/login?mode=register"); return; }
    if (user.role !== "consumer") { toast.error("Hanya akun Peminat yang dapat memesan unit"); return; }
    setSelected(unit);
  };

  const confirmBooking = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/bookings", { unit_id: selected.id, ...bookingCfg });
      toast.success("Pemesanan dibuat. Lanjutkan pembayaran di portal.");
      setSelected(null);
      navigate("/portal", { state: { openBooking: data.id } });
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    } finally { setBusy(false); }
  };

  if (!project) return <div className="min-h-screen"><Navbar /><div className="grid place-items-center py-40 text-slate-400">Memuat...</div></div>;

  const projectMapsUrl = project.lat != null && project.lng != null
    ? `https://www.google.com/maps/search/?api=1&query=${project.lat},${project.lng}`
    : null;
  const projectRouteUrl = project.lat != null && project.lng != null
    ? `https://www.google.com/maps/dir/?api=1&destination=${project.lat},${project.lng}&travelmode=driving`
    : null;

  return (
    <div className="App">
      <Navbar />
      <div className="relative h-64 sm:h-80 overflow-hidden">
        <img src={mediaUrl(project.image)} alt={project.name} className="w-full h-full object-cover" />
        <div className="absolute inset-0 hero-overlay" />
        <div className="absolute bottom-0 left-0 right-0 max-w-7xl mx-auto px-4 sm:px-6 pb-6">
          <button onClick={() => navigate("/")} className="flex items-center gap-1.5 text-white/80 hover:text-white text-sm mb-3">
            <ArrowLeft className="h-4 w-4" /> Semua proyek
          </button>
          <h1 className="font-heading text-3xl sm:text-4xl font-bold text-white">{project.name}</h1>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-1.5">
            <p className="flex items-center gap-1.5 text-white/85"><MapPin className="h-4 w-4" /> {project.location} · {project.developer_name}</p>
            {project.lat != null && project.lng != null && (
              <a href={projectMapsUrl} target="_blank" rel="noreferrer" data-testid="project-gps-pin"
                className="inline-flex items-center gap-1.5 rounded-full bg-white/90 hover:bg-white text-[hsl(var(--primary))] text-xs font-semibold px-3 py-1.5 transition-colors shadow-sm">
                <MapPinned className="h-3.5 w-3.5" /> Pin Lokasi Proyek di Maps
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <h2 className="font-heading text-2xl font-bold text-slate-800">Denah Blok / Kavling</h2>
          <p className="text-slate-500 mt-1 mb-4">Klik kavling <b>Tersedia</b> untuk melihat detail & memesan unit.</p>
          <BlockPlan units={project.units} onSelect={(u) => setUnitDetail(u)} />

          <h2 className="font-heading text-2xl font-bold text-slate-800 mt-10">Daftar Unit</h2>
          <p className="text-slate-500 mt-1">{project.description}</p>
          <div className="mt-6 space-y-3">
            {project.units.map((u) => (
              <div key={u.id} data-testid={`unit-row-${u.id}`}
                className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-sm flex flex-wrap items-center gap-4 card-hover">
                <button onClick={() => setUnitDetail(u)} data-testid={`unit-detail-open-${u.id}`}
                  className="flex items-center gap-4 flex-1 min-w-[180px] text-left group">
                  {u.image_front ? (
                    <img src={mediaUrl(u.image_front)} alt={u.type} className="h-14 w-20 rounded-lg object-cover border border-slate-200 group-hover:opacity-90" />
                  ) : (
                    <div className="h-12 w-12 rounded-lg bg-[hsl(var(--secondary))] grid place-items-center">
                      <Home className="h-6 w-6 text-[hsl(var(--primary))]" />
                    </div>
                  )}
                  <div>
                    <p className="font-semibold text-slate-800 group-hover:text-[hsl(var(--primary))]">{u.type}</p>
                    <p className="text-sm text-slate-500 flex items-center gap-3">
                      <span>Blok {u.block}/{u.number}</span>
                      <span className="flex items-center gap-1"><Maximize className="h-3.5 w-3.5" /> LT {u.land_area} · LB {u.building_area} m²</span>
                    </p>
                  </div>
                </button>
                <div className="text-right">
                  <p className="font-heading font-bold text-[hsl(var(--primary))]">{rupiah(u.price)}</p>
                  <div className="mt-1"><StatusBadge status={u.status} /></div>
                </div>
                <Button disabled={u.status !== "available"} onClick={() => openBooking(u)}
                  data-testid={`book-unit-${u.id}`}
                  className="bg-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/90 disabled:opacity-40">
                  {u.status === "available" ? "Pesan Unit" : "Tidak tersedia"}
                </Button>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:sticky lg:top-20 h-fit">
          <KprSimulator price={project.units[0]?.price || 200000000} defaultProgram={project.program} />
        </div>
      </div>

      {/* Unit detail dialog */}
      <Dialog open={!!unitDetail} onOpenChange={(o) => !o && setUnitDetail(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle data-testid="unit-detail-title">{unitDetail?.type} — Blok {unitDetail?.block}/{unitDetail?.number}</DialogTitle>
            <DialogDescription>{project.name} · {project.location}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <UnitGallery
              images={[unitDetail?.image_front, ...(unitDetail?.gallery || [])]}
              fallback={project.image}
              alt={unitDetail?.type} label={`${unitDetail?.type || "Rumah"} — Foto`} />
            <VideoGallery videos={unitDetail?.videos} />
            {(unitDetail?.image_layout || unitDetail?.image_siteplan) && (
              <div className="grid grid-cols-2 gap-3">
                {unitDetail?.image_layout && (
                  <div><p className="text-xs text-slate-500 mb-1">Layout Rumah</p>
                    <ZoomableImage src={unitDetail.image_layout} alt="Layout" label="Layout Rumah"
                      testid="unit-detail-layout" className="h-40 rounded-lg border border-slate-200" /></div>
                )}
                {unitDetail?.image_siteplan && (
                  <div><p className="text-xs text-slate-500 mb-1">Siteplan</p>
                    <ZoomableImage src={unitDetail.image_siteplan} alt="Siteplan" label="Siteplan"
                      testid="unit-detail-siteplan" className="h-40 rounded-lg border border-slate-200" /></div>
                )}
              </div>
            )}
            {unitDetail?.image_location_map && (
              <div>
                <p className="text-xs text-slate-500 mb-1 flex items-center gap-1"><MapPin className="h-3.5 w-3.5" /> Peta Lokasi dari Jalan Raya</p>
                <ZoomableImage src={unitDetail.image_location_map} alt="Peta Lokasi" label="Peta Lokasi dari Jalan Raya"
                  testid="unit-detail-location-map" className="h-48 rounded-lg border border-slate-200" />
              </div>
            )}
            {projectMapsUrl && (
              <div className="flex flex-wrap gap-2">
                <a href={projectMapsUrl} target="_blank" rel="noreferrer" data-testid="unit-detail-project-pin"
                  className="flex-1 min-w-[160px] flex items-center justify-between gap-2 rounded-lg border border-[hsl(var(--primary))]/30 bg-[hsl(var(--secondary))]/40 px-4 py-3 text-sm hover:bg-[hsl(var(--secondary))]/70 transition-colors">
                  <span className="flex items-center gap-2 text-slate-700"><MapPinned className="h-4 w-4 text-[hsl(var(--primary))]" /> Pin lokasi proyek {project.name}</span>
                  <span className="text-[hsl(var(--primary))] font-medium whitespace-nowrap">Lihat →</span>
                </a>
                <a href={projectRouteUrl} target="_blank" rel="noreferrer" data-testid="unit-detail-project-route"
                  className="flex items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-3 text-sm font-medium text-white hover:bg-[hsl(var(--primary))]/90 transition-colors">
                  <Route className="h-4 w-4" /> Rute ke proyek
                </a>
              </div>
            )}
            {unitDetail?.gps_coordinates && (
              <div className="flex flex-wrap gap-2">
                <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(unitDetail.gps_coordinates)}`}
                  target="_blank" rel="noreferrer" data-testid="unit-detail-gps-link"
                  className="flex-1 min-w-[160px] flex items-center justify-between gap-2 rounded-lg border border-[hsl(var(--accent))]/30 bg-amber-50/50 px-4 py-3 text-sm hover:bg-amber-50 transition-colors">
                  <span className="flex items-center gap-2 text-slate-700"><Navigation className="h-4 w-4 text-[hsl(var(--accent))]" /> Pin GPS unit: {unitDetail.gps_coordinates}</span>
                  <span className="text-[hsl(var(--accent))] font-medium whitespace-nowrap">Lihat →</span>
                </a>
                <a href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(unitDetail.gps_coordinates)}&travelmode=driving`}
                  target="_blank" rel="noreferrer" data-testid="unit-detail-route-btn"
                  className="flex items-center gap-2 rounded-lg bg-[hsl(var(--accent))] px-4 py-3 text-sm font-medium text-white hover:bg-[hsl(var(--accent))]/90 transition-colors">
                  <Route className="h-4 w-4" /> Rute ke unit
                </a>
              </div>
            )}
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm bg-[hsl(var(--muted))]/50 rounded-lg p-4">
              <p className="text-slate-500">Harga</p><p className="font-semibold text-[hsl(var(--primary))]">{rupiah(unitDetail?.price)}</p>
              <p className="text-slate-500">Luas Tanah / Bangunan</p><p className="text-slate-700">{unitDetail?.land_area} / {unitDetail?.building_area} m²</p>
              <p className="text-slate-500">Status</p><p><StatusBadge status={unitDetail?.status} /></p>
              <p className="text-slate-500">Alamat Detail</p><p className="text-slate-700">{unitDetail?.address_detail || `${project.name}, ${project.location}`}</p>
            </div>
            <KprSimulator price={unitDetail?.price || 0} defaultProgram={bookingCfg.program} />
            <Button disabled={unitDetail?.status !== "available"} onClick={() => { const u = unitDetail; setUnitDetail(null); openBooking(u); }}
              data-testid="detail-book-btn" className="w-full bg-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/90 disabled:opacity-40">
              {unitDetail?.status === "available" ? "Pesan Unit & Bayar" : "Unit tidak tersedia"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Booking dialog */}
      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Pesan Unit {selected?.type}</DialogTitle>
            <DialogDescription>Blok {selected?.block}/{selected?.number} · {rupiah(selected?.price)}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2">
              {["FLPP", "KOMERSIAL"].map((p) => (
                <button key={p} onClick={() => setBookingCfg({ ...bookingCfg, program: p })}
                  data-testid={`booking-program-${p}`}
                  className={`text-sm font-medium rounded-lg py-2 border ${bookingCfg.program === p ? "bg-[hsl(var(--primary))] text-white" : "border-slate-200 text-slate-600"}`}>
                  {p === "FLPP" ? "FLPP Subsidi" : "Komersial"}
                </button>
              ))}
            </div>
            <div>
              <div className="flex justify-between mb-2"><Label>DP</Label><span className="text-sm font-semibold text-[hsl(var(--primary))]">{bookingCfg.dp_percent}%</span></div>
              <Slider value={[bookingCfg.dp_percent]} min={0} max={50} step={1} onValueChange={(v) => setBookingCfg({ ...bookingCfg, dp_percent: v[0] })} />
            </div>
            <div>
              <div className="flex justify-between mb-2"><Label>Tenor</Label><span className="text-sm font-semibold text-[hsl(var(--primary))]">{bookingCfg.tenor_years} thn</span></div>
              <Slider value={[bookingCfg.tenor_years]} min={5} max={30} step={1} onValueChange={(v) => setBookingCfg({ ...bookingCfg, tenor_years: v[0] })} />
            </div>
            <div>
              <Label className="mb-2 block">Metode Pembayaran Booking Fee</Label>
              <div className="grid grid-cols-2 gap-2">
                {[{ k: "QRIS", i: QrCode, t: "QRIS" }, { k: "VA_BTN", i: CreditCard, t: "VA BTN" }].map((m) => (
                  <button key={m.k} onClick={() => setBookingCfg({ ...bookingCfg, payment_method: m.k })}
                    data-testid={`booking-method-${m.k}`}
                    className={`flex items-center gap-2 justify-center text-sm rounded-lg py-2.5 border ${bookingCfg.payment_method === m.k ? "border-[hsl(var(--primary))] bg-[hsl(var(--secondary))]/40 text-[hsl(var(--primary))]" : "border-slate-200 text-slate-600"}`}>
                    <m.i className="h-4 w-4" /> {m.t}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Estimasi Down Payment (DP {bookingCfg.dp_percent}%)</span>
              <span className="font-medium text-slate-700">{rupiah((selected?.price || 0) * bookingCfg.dp_percent / 100)}</span>
            </div>
            <div className="bg-[hsl(var(--muted))] rounded-lg p-3 flex justify-between">
              <span className="text-sm text-slate-600">Booking Fee / Uang Tanda Jadi (dibayar sekarang)</span>
              <span className="font-semibold text-[hsl(var(--primary))]">{rupiah(5000000)}</span>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={confirmBooking} disabled={busy} data-testid="confirm-booking-btn"
              className="w-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
              {busy ? "Memproses..." : "Buat Pemesanan"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
