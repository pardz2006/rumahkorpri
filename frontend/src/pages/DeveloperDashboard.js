import React, { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Navbar } from "../components/Navbar";
import { StatusBadge, fileToDataUrl } from "../components/shared";
import { api, rupiah, BACKEND, formatApiErrorDetail, mediaUrl } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "../components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "../components/ui/alert-dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { FileDown, PenLine, Stamp, FileText, Plus, Building2, ImagePlus, Pencil, Trash2, Home, Copy, MapPin, CopyPlus } from "lucide-react";

function SignaturePad({ onChange }) {
  const canvasRef = useRef(null);
  const drawing = useRef(false);

  const pos = (e) => {
    const r = canvasRef.current.getBoundingClientRect();
    const t = e.touches ? e.touches[0] : e;
    return { x: t.clientX - r.left, y: t.clientY - r.top };
  };
  const start = (e) => { drawing.current = true; const ctx = canvasRef.current.getContext("2d"); const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); };
  const move = (e) => {
    if (!drawing.current) return;
    const ctx = canvasRef.current.getContext("2d");
    const p = pos(e); ctx.lineWidth = 2.5; ctx.lineCap = "round"; ctx.strokeStyle = "#0F5132";
    ctx.lineTo(p.x, p.y); ctx.stroke();
  };
  const end = () => { if (drawing.current) { drawing.current = false; onChange(canvasRef.current.toDataURL("image/png")); } };
  const clear = () => { const c = canvasRef.current; c.getContext("2d").clearRect(0, 0, c.width, c.height); onChange(null); };

  return (
    <div>
      <canvas ref={canvasRef} width={420} height={150} data-testid="signature-canvas"
        onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end}
        onTouchStart={start} onTouchMove={move} onTouchEnd={end}
        className="w-full border-2 border-dashed border-slate-300 rounded-lg bg-slate-50 touch-none cursor-crosshair" />
      <button onClick={clear} type="button" className="text-xs text-slate-400 hover:text-red-500 mt-1">Bersihkan tanda tangan</button>
    </div>
  );
}

function ImageInput({ label, value, onChange, testid }) {
  const pick = async (e) => {
    const f = e.target.files?.[0];
    if (f) onChange(await fileToDataUrl(f));
  };
  return (
    <div>
      <Label className="text-xs text-slate-500">{label}</Label>
      <label className="mt-1 block cursor-pointer">
        <input type="file" accept="image/*" className="hidden" data-testid={testid} onChange={pick} />
        {value ? (
          <img src={mediaUrl(value)} alt={label} className="h-24 w-full object-cover rounded-lg border border-slate-200" />
        ) : (
          <div className="h-24 rounded-lg border-2 border-dashed border-slate-300 grid place-items-center text-slate-400 hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors">
            <ImagePlus className="h-6 w-6" />
          </div>
        )}
      </label>
    </div>
  );
}

function GalleryInput({ value = [], onChange, testid }) {
  const add = async (e) => {
    const files = Array.from(e.target.files || []);
    const urls = await Promise.all(files.map((f) => fileToDataUrl(f)));
    onChange([...(value || []), ...urls]);
    e.target.value = "";
  };
  const remove = (i) => onChange(value.filter((_, idx) => idx !== i));
  return (
    <div>
      <Label className="text-xs text-slate-500">Galeri Foto Rumah (beberapa foto — peminat dapat menggeser)</Label>
      <div className="mt-1 flex flex-wrap gap-2">
        {(value || []).map((g, i) => (
          <div key={i} className="relative h-20 w-24 rounded-lg overflow-hidden border border-slate-200 group">
            <img src={mediaUrl(g)} alt={`galeri ${i + 1}`} className="h-full w-full object-cover" />
            <button type="button" onClick={() => remove(i)} data-testid={`${testid}-remove-${i}`}
              className="absolute top-1 right-1 h-6 w-6 grid place-items-center rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        <label className="h-20 w-24 rounded-lg border-2 border-dashed border-slate-300 grid place-items-center text-slate-400 hover:border-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] transition-colors cursor-pointer">
          <input type="file" accept="image/*" multiple className="hidden" data-testid={testid} onChange={add} />
          <ImagePlus className="h-6 w-6" />
        </label>
      </div>
    </div>
  );
}

export default function DeveloperDashboard() {
  const [queue, setQueue] = useState([]);
  const [approveFor, setApproveFor] = useState(null);
  const [signature, setSignature] = useState(null);
  const [busy, setBusy] = useState(false);
  const [projects, setProjects] = useState([]);
  const [showProject, setShowProject] = useState(false);
  const [editProjectId, setEditProjectId] = useState(null);
  const [showUnit, setShowUnit] = useState(false);
  const [editUnitId, setEditUnitId] = useState(null);
  const [deleteUnit, setDeleteUnit] = useState(null);
  const [saving, setSaving] = useState(false);
  const emptyProject = { name: "", location: "", address_detail: "", developer_name: "", description: "", image: null, program: "KOMERSIAL", bank: "Bank BTN" };
  const emptyUnit = { project_id: "", type: "", block: "", number: "", price: "", land_area: "", building_area: "", address_detail: "", image_front: null, image_layout: null, image_siteplan: null, image_location_map: null, gps_coordinates: "", gallery: [], bulk: false, start_number: 1, count: 5 };
  const [projectForm, setProjectForm] = useState(emptyProject);
  const [unitForm, setUnitForm] = useState(emptyUnit);

  const load = () => {
    api.get("/developer/spr-queue").then((r) => setQueue(r.data)).catch(() => {});
    api.get("/developer/projects").then((r) => setProjects(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const openAddUnit = () => {
    setEditUnitId(null); setUnitForm({ ...emptyUnit }); setShowUnit(true);
  };

  const openEditUnit = (u, projectId) => {
    setEditUnitId(u.id);
    setUnitForm({
      project_id: projectId, type: u.type || "", block: u.block || "", number: u.number || "",
      price: u.price ?? "", land_area: u.land_area ?? "", building_area: u.building_area ?? "",
      address_detail: u.address_detail || "",
      image_front: u.image_front || null, image_layout: u.image_layout || null, image_siteplan: u.image_siteplan || null,
      image_location_map: u.image_location_map || null, gps_coordinates: u.gps_coordinates || "",
      gallery: u.gallery || [], bulk: false, start_number: 1, count: 5,
    });
    setShowUnit(true);
  };

  const openCloneUnit = (u, projectId) => {
    setEditUnitId(null);
    setUnitForm({
      project_id: projectId, type: u.type || "", block: u.block || "", number: "",
      price: u.price ?? "", land_area: u.land_area ?? "", building_area: u.building_area ?? "",
      address_detail: u.address_detail || "",
      image_front: u.image_front || null, image_layout: u.image_layout || null, image_siteplan: u.image_siteplan || null,
      image_location_map: u.image_location_map || null, gps_coordinates: u.gps_coordinates || "",
      gallery: u.gallery || [], bulk: false, start_number: 1, count: 5,
    });
    setShowUnit(true);
    toast.info("Data unit disalin. Ubah Blok & No. Unit lalu simpan.");
  };

  const openAddProject = () => {
    setEditProjectId(null); setProjectForm(emptyProject); setShowProject(true);
  };

  const openEditProject = (p) => {
    setEditProjectId(p.id);
    setProjectForm({
      name: p.name || "", location: p.location || "", address_detail: p.address_detail || "",
      developer_name: p.developer_name || "", description: p.description || "",
      image: p.image || null, program: p.program || "KOMERSIAL", bank: p.bank || "Bank BTN",
    });
    setShowProject(true);
  };

  const submitProject = async () => {
    setSaving(true);
    try {
      if (editProjectId) {
        await api.put(`/developer/projects/${editProjectId}`, projectForm);
        toast.success("Proyek berhasil diperbarui");
      } else {
        await api.post("/developer/projects", projectForm);
        toast.success("Proyek baru berhasil ditambahkan");
      }
      setShowProject(false); setEditProjectId(null); setProjectForm(emptyProject); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const submitUnit = async () => {
    if (!unitForm.project_id) { toast.error("Pilih proyek terlebih dahulu"); return; }
    setSaving(true);
    const payload = {
      ...unitForm,
      price: Number(unitForm.price),
      land_area: unitForm.land_area ? Number(unitForm.land_area) : null,
      building_area: unitForm.building_area ? Number(unitForm.building_area) : null,
    };
    try {
      if (editUnitId) {
        await api.put(`/developer/units/${editUnitId}`, payload);
        toast.success("Unit berhasil diperbarui");
      } else if (unitForm.bulk) {
        const { data } = await api.post("/developer/units/bulk", {
          ...payload,
          start_number: Number(unitForm.start_number) || 1,
          count: Number(unitForm.count) || 1,
        });
        toast.success(`${data.created} unit berurutan berhasil dibuat (No. ${data.numbers[0]}–${data.numbers[data.numbers.length - 1]})`);
      } else {
        await api.post("/developer/units", payload);
        toast.success("Unit berhasil ditambahkan & siap dipesan peminat");
      }
      setShowUnit(false); setEditUnitId(null); setUnitForm({ ...emptyUnit }); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const confirmDelete = async () => {
    try {
      await api.delete(`/developer/units/${deleteUnit.id}`);
      toast.success("Unit berhasil dihapus");
      setDeleteUnit(null); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const approve = async () => {
    setBusy(true);
    try {
      await api.post(`/bookings/${approveFor.id}/spr/approve`, { signature });
      toast.success("SPR disetujui & diterbitkan. Notifikasi WA terkirim ke peminat.");
      setApproveFor(null); setSignature(null); load();
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const drafts = queue.filter((b) => b.spr_status === "draft");
  const issued = queue.filter((b) => b.spr_status === "issued");

  return (
    <div className="App">
      <Navbar />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-heading text-3xl font-bold text-slate-800">Dashboard Mitra Developer</h1>
            <p className="text-slate-500 mt-1">Tambah proyek & unit, tinjau pembayaran, setujui SPR.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={openAddProject} data-testid="add-project-btn">
              <Building2 className="h-4 w-4 mr-1.5" /> Tambah Proyek
            </Button>
            <Button onClick={openAddUnit} data-testid="add-unit-btn"
              className="bg-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/90">
              <Plus className="h-4 w-4 mr-1.5" /> Tambah Unit
            </Button>
          </div>
        </div>

        <section className="mt-8">
          <h2 className="font-heading text-lg font-semibold text-slate-700 flex items-center gap-2">
            <PenLine className="h-5 w-5 text-[hsl(var(--accent))]" /> Menunggu Persetujuan SPR
            <span className="text-sm font-normal text-slate-400">({drafts.length})</span>
          </h2>
          <div className="mt-4 grid md:grid-cols-2 gap-4">
            {drafts.length === 0 && <p className="text-slate-400">Tidak ada draft SPR menunggu.</p>}
            {drafts.map((b) => (
              <div key={b.id} data-testid={`spr-draft-${b.id}`} className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm card-hover">
                <div className="flex items-center justify-between">
                  <p className="font-heading font-semibold text-slate-800">{b.unit?.type}</p>
                  <StatusBadge status="draft" />
                </div>
                <p className="text-sm text-slate-500 mt-1">{b.project?.name} · Blok {b.unit?.block}/{b.unit?.number}</p>
                <div className="mt-3 text-sm text-slate-600 space-y-0.5">
                  <p>Peminat: <b>{b.consumer?.name}</b></p>
                  <p>Booking fee: {rupiah(b.booking_fee)} · <StatusBadge status={b.payment_status} /></p>
                  <p>No. SPR: {b.spr_number}</p>
                </div>
                <Button onClick={() => setApproveFor(b)} data-testid={`approve-open-${b.id}`}
                  className="w-full mt-4 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
                  <Stamp className="h-4 w-4 mr-1.5" /> Tinjau & Setujui SPR
                </Button>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="font-heading text-lg font-semibold text-slate-700 flex items-center gap-2">
            <FileText className="h-5 w-5 text-[hsl(var(--primary))]" /> SPR Terbit ({issued.length})
          </h2>
          <div className="mt-4 space-y-2">
            {issued.map((b) => (
              <div key={b.id} className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-sm flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-800">{b.consumer?.name} — {b.unit?.type}</p>
                  <p className="text-xs text-slate-400">{b.spr_number} · {b.project?.name}</p>
                </div>
                <Button asChild variant="outline" size="sm" data-testid={`dev-spr-download-${b.id}`}>
                  <a href={`${BACKEND}/api/bookings/${b.id}/spr.pdf`} target="_blank" rel="noreferrer">
                    <FileDown className="h-4 w-4 mr-1.5" /> SPR PDF
                  </a>
                </Button>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="font-heading text-lg font-semibold text-slate-700 flex items-center gap-2">
            <Home className="h-5 w-5 text-[hsl(var(--primary))]" /> Kelola Unit
          </h2>
          <div className="mt-4 space-y-6">
            {projects.length === 0 && <p className="text-slate-400">Belum ada proyek. Tambahkan proyek terlebih dahulu.</p>}
            {projects.map((p) => (
              <div key={p.id} data-testid={`manage-project-${p.id}`}>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-slate-800">{p.name} <span className="text-sm font-normal text-slate-400">· {p.location} · {p.units.length} unit</span></p>
                  <button onClick={() => openEditProject(p)} data-testid={`edit-project-${p.id}`}
                    className="h-7 px-2 inline-flex items-center gap-1 rounded-lg hover:bg-slate-100 text-slate-500 text-xs">
                    <Pencil className="h-3.5 w-3.5" /> Edit Proyek
                  </button>
                </div>
                <div className="mt-2 grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {p.units.map((u) => (
                    <div key={u.id} data-testid={`manage-unit-${u.id}`} className="bg-white rounded-xl border border-slate-200/80 p-3 shadow-sm flex gap-3">
                      {u.image_front ? (
                        <img src={mediaUrl(u.image_front)} alt={u.type} className="h-16 w-16 rounded-lg object-cover border border-slate-200 shrink-0" />
                      ) : (
                        <div className="h-16 w-16 rounded-lg bg-[hsl(var(--secondary))] grid place-items-center shrink-0"><Home className="h-6 w-6 text-[hsl(var(--primary))]" /></div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-800 text-sm truncate">{u.type}</p>
                        <p className="text-xs text-slate-500">Blok {u.block}/{u.number}</p>
                        <p className="text-sm font-semibold text-[hsl(var(--primary))]">{rupiah(u.price)}</p>
                        <div className="flex items-center gap-2 mt-1.5">
                          <StatusBadge status={u.status} />
                          <button onClick={() => openCloneUnit(u, p.id)} data-testid={`clone-unit-${u.id}`}
                            className="h-7 w-7 grid place-items-center rounded-lg hover:bg-slate-100 text-slate-500" title="Duplikat unit">
                            <Copy className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => openEditUnit(u, p.id)} data-testid={`edit-unit-${u.id}`}
                            className="h-7 w-7 grid place-items-center rounded-lg hover:bg-slate-100 text-slate-500" title="Edit">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => setDeleteUnit(u)} data-testid={`delete-unit-${u.id}`}
                            disabled={u.status !== "available"}
                            className="h-7 w-7 grid place-items-center rounded-lg hover:bg-red-50 text-red-500 disabled:opacity-30 disabled:hover:bg-transparent" title="Hapus">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Dialog tambah proyek */}
      <Dialog open={showProject} onOpenChange={setShowProject}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editProjectId ? "Edit Proyek" : "Tambah Proyek Perumahan"}</DialogTitle>
            <DialogDescription>Proyek baru langsung tampil di landing page peminat.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div><Label className="text-xs">Nama Proyek</Label><Input data-testid="pf-name" value={projectForm.name} onChange={(e) => setProjectForm({ ...projectForm, name: e.target.value })} /></div>
              <div><Label className="text-xs">Lokasi (Kota)</Label><Input data-testid="pf-location" value={projectForm.location} onChange={(e) => setProjectForm({ ...projectForm, location: e.target.value })} /></div>
            </div>
            <div><Label className="text-xs">Alamat Detail</Label><Input data-testid="pf-address" placeholder="Jl., RT/RW, Kelurahan, Kecamatan..." value={projectForm.address_detail} onChange={(e) => setProjectForm({ ...projectForm, address_detail: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label className="text-xs">Nama Developer</Label><Input data-testid="pf-developer" value={projectForm.developer_name} onChange={(e) => setProjectForm({ ...projectForm, developer_name: e.target.value })} /></div>
              <div>
                <Label className="text-xs">Program KPR</Label>
                <Select value={projectForm.program} onValueChange={(v) => setProjectForm({ ...projectForm, program: v })}>
                  <SelectTrigger data-testid="pf-program"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="FLPP">FLPP (Subsidi)</SelectItem>
                    <SelectItem value="KOMERSIAL">Komersial</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div><Label className="text-xs">Deskripsi</Label><Textarea data-testid="pf-description" value={projectForm.description} onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })} /></div>
            <div>
              <Label className="text-xs">Bank Pembiayaan KPR</Label>
              <Select value={projectForm.bank} onValueChange={(v) => setProjectForm({ ...projectForm, bank: v })}>
                <SelectTrigger data-testid="pf-bank"><SelectValue placeholder="Pilih bank" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Bank BTN">Bank BTN</SelectItem>
                  <SelectItem value="Bank DKI">Bank DKI</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-[11px] text-slate-400 mt-1">Pengajuan KPR proyek ini hanya diteruskan ke analis bank terpilih.</p>
            </div>
            <ImageInput label="Foto Proyek / Banner" value={projectForm.image} onChange={(v) => setProjectForm({ ...projectForm, image: v })} testid="pf-image" />
          </div>
          <DialogFooter>
            <Button onClick={submitProject} disabled={saving || !projectForm.name || !projectForm.location} data-testid="submit-project-btn"
              className="w-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
              {saving ? "Menyimpan..." : editProjectId ? "Simpan Perubahan" : "Simpan Proyek"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog tambah unit */}
      <Dialog open={showUnit} onOpenChange={setShowUnit}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editUnitId ? "Edit Unit" : "Tambah Unit yang Ditawarkan"}</DialogTitle>
            <DialogDescription>Lengkapi detail harga, foto tampak depan, layout, siteplan & alamat.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Proyek</Label>
              <Select value={unitForm.project_id} onValueChange={(v) => setUnitForm({ ...unitForm, project_id: v })}>
                <SelectTrigger data-testid="uf-project"><SelectValue placeholder="Pilih proyek" /></SelectTrigger>
                <SelectContent>
                  {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name} — {p.location}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div><Label className="text-xs">Tipe Rumah</Label><Input data-testid="uf-type" placeholder="Tipe 45/90" value={unitForm.type} onChange={(e) => setUnitForm({ ...unitForm, type: e.target.value })} /></div>
              <div><Label className="text-xs">Blok</Label><Input data-testid="uf-block" placeholder="B" value={unitForm.block} onChange={(e) => setUnitForm({ ...unitForm, block: e.target.value })} /></div>
              <div><Label className="text-xs">No. Unit</Label><Input data-testid="uf-number" placeholder="12" disabled={unitForm.bulk} value={unitForm.bulk ? "" : unitForm.number} onChange={(e) => setUnitForm({ ...unitForm, number: e.target.value })} /></div>
            </div>
            {!editUnitId && (
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" data-testid="uf-bulk-toggle" checked={unitForm.bulk}
                    onChange={(e) => setUnitForm({ ...unitForm, bulk: e.target.checked })}
                    className="h-4 w-4 accent-[hsl(var(--primary))]" />
                  <span className="text-sm font-medium text-slate-700 flex items-center gap-1.5"><CopyPlus className="h-4 w-4 text-[hsl(var(--accent))]" /> Duplikat Massal (buat No. berurutan)</span>
                </label>
                {unitForm.bulk && (
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <div><Label className="text-xs">Mulai dari No.</Label><Input type="number" min={1} data-testid="uf-start-number" value={unitForm.start_number} onChange={(e) => setUnitForm({ ...unitForm, start_number: e.target.value })} /></div>
                    <div><Label className="text-xs">Jumlah Unit</Label><Input type="number" min={1} max={50} data-testid="uf-count" value={unitForm.count} onChange={(e) => setUnitForm({ ...unitForm, count: e.target.value })} /></div>
                    <p className="col-span-2 text-[11px] text-slate-500">
                      Akan dibuat {Number(unitForm.count) || 0} unit di Blok {unitForm.block?.toUpperCase() || "?"}: No.{" "}
                      {String(Number(unitForm.start_number) || 1).padStart(2, "0")}–{String((Number(unitForm.start_number) || 1) + (Number(unitForm.count) || 1) - 1).padStart(2, "0")} dengan data & foto yang sama.
                    </p>
                  </div>
                )}
              </div>
            )}
            <div className="grid grid-cols-3 gap-3">
              <div><Label className="text-xs">Harga (Rp)</Label><Input type="number" data-testid="uf-price" placeholder="350000000" value={unitForm.price} onChange={(e) => setUnitForm({ ...unitForm, price: e.target.value })} /></div>
              <div><Label className="text-xs">Luas Tanah (m²)</Label><Input type="number" data-testid="uf-land" value={unitForm.land_area} onChange={(e) => setUnitForm({ ...unitForm, land_area: e.target.value })} /></div>
              <div><Label className="text-xs">Luas Bangunan (m²)</Label><Input type="number" data-testid="uf-building" value={unitForm.building_area} onChange={(e) => setUnitForm({ ...unitForm, building_area: e.target.value })} /></div>
            </div>
            <div><Label className="text-xs">Alamat Detail Unit</Label><Input data-testid="uf-address" placeholder="Blok B No.12, Jl. Harmoni Raya, Bekasi Timur..." value={unitForm.address_detail} onChange={(e) => setUnitForm({ ...unitForm, address_detail: e.target.value })} /></div>
            <div>
              <Label className="text-xs flex items-center gap-1"><MapPin className="h-3 w-3" /> Koordinat GPS Proyek</Label>
              <Input data-testid="uf-gps" placeholder="-6.2415, 106.9925 (lat, lng)" value={unitForm.gps_coordinates} onChange={(e) => setUnitForm({ ...unitForm, gps_coordinates: e.target.value })} />
              <p className="text-[11px] text-slate-400 mt-1">Salin dari Google Maps (klik kanan lokasi → koordinat). Peminat dapat langsung membukanya di Maps.</p>
            </div>
            <ImageInput label="Foto Rumah Tampak Depan" value={unitForm.image_front} onChange={(v) => setUnitForm({ ...unitForm, image_front: v })} testid="uf-image-front" />
            <div className="grid grid-cols-2 gap-3">
              <ImageInput label="Layout Rumah" value={unitForm.image_layout} onChange={(v) => setUnitForm({ ...unitForm, image_layout: v })} testid="uf-image-layout" />
              <ImageInput label="Siteplan" value={unitForm.image_siteplan} onChange={(v) => setUnitForm({ ...unitForm, image_siteplan: v })} testid="uf-image-siteplan" />
            </div>
            <ImageInput label="Peta Lokasi dari Jalan Raya" value={unitForm.image_location_map} onChange={(v) => setUnitForm({ ...unitForm, image_location_map: v })} testid="uf-image-location-map" />
            <GalleryInput value={unitForm.gallery} onChange={(v) => setUnitForm({ ...unitForm, gallery: v })} testid="uf-gallery" />
          </div>
          <DialogFooter>
            <Button onClick={submitUnit} disabled={saving || !unitForm.type || !unitForm.price || !unitForm.project_id} data-testid="submit-unit-btn"
              className="w-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
              {saving ? "Menyimpan..." : editUnitId ? "Simpan Perubahan" : "Simpan Unit"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hapus unit konfirmasi */}
      <AlertDialog open={!!deleteUnit} onOpenChange={(o) => !o && setDeleteUnit(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Hapus unit {deleteUnit?.type}?</AlertDialogTitle>
            <AlertDialogDescription>
              Unit Blok {deleteUnit?.block}/{deleteUnit?.number} akan dihapus permanen. Tindakan ini tidak dapat dibatalkan.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="cancel-delete-btn">Batal</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} data-testid="confirm-delete-btn" className="bg-red-600 hover:bg-red-700">Hapus</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={!!approveFor} onOpenChange={(o) => { if (!o) { setApproveFor(null); setSignature(null); } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Setujui SPR {approveFor?.spr_number}</DialogTitle>
            <DialogDescription>Bubuhkan tanda tangan / stempel digital developer.</DialogDescription>
          </DialogHeader>
          <div className="bg-[hsl(var(--muted))]/50 rounded-lg p-3 text-sm text-slate-600 space-y-0.5">
            <p>Peminat: <b>{approveFor?.consumer?.name}</b></p>
            <p>Unit: {approveFor?.unit?.type} · {rupiah(approveFor?.unit?.price)}</p>
          </div>
          <div className="mt-2">
            <p className="text-sm text-slate-600 mb-1.5">Tanda Tangan Digital</p>
            <SignaturePad onChange={setSignature} />
          </div>
          <DialogFooter>
            <Button onClick={approve} disabled={busy} data-testid="approve-spr-btn"
              className="w-full bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))]/90">
              {busy ? "Menerbitkan..." : "Terbitkan SPR & Teruskan ke BTN"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
