import React from "react";

const MAP = {
  available: { t: "Tersedia", c: "bg-emerald-100 text-emerald-700" },
  booked: { t: "Dipesan", c: "bg-amber-100 text-amber-700" },
  sold: { t: "Terjual", c: "bg-slate-200 text-slate-600" },
  pending: { t: "Menunggu", c: "bg-amber-100 text-amber-700" },
  paid: { t: "Lunas", c: "bg-emerald-100 text-emerald-700" },
  failed: { t: "Gagal", c: "bg-red-100 text-red-700" },
  not_ready: { t: "Belum siap", c: "bg-slate-100 text-slate-500" },
  draft: { t: "Draft SPR", c: "bg-blue-100 text-blue-700" },
  approved: { t: "Disetujui", c: "bg-emerald-100 text-emerald-700" },
  issued: { t: "SPR Terbit", c: "bg-emerald-100 text-emerald-700" },
  missing: { t: "Belum ada", c: "bg-red-100 text-red-700" },
  uploaded: { t: "Terunggah", c: "bg-blue-100 text-blue-700" },
  valid: { t: "Valid", c: "bg-emerald-100 text-emerald-700" },
  invalid: { t: "Tidak valid", c: "bg-red-100 text-red-700" },
  pre_approved: { t: "Pra-Disetujui", c: "bg-teal-100 text-teal-700" },
  rejected: { t: "Ditolak", c: "bg-red-100 text-red-700" },
  need_revision: { t: "Perlu Revisi", c: "bg-orange-100 text-orange-700" },
};

export function StatusBadge({ status }) {
  const m = MAP[status] || { t: status, c: "bg-slate-100 text-slate-600" };
  return (
    <span data-testid={`status-${status}`} className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${m.c}`}>
      {m.t}
    </span>
  );
}

export function StatCard({ label, value, icon: Icon, accent }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-sm card-hover">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{label}</p>
        {Icon && (
          <div className={`h-9 w-9 rounded-lg grid place-items-center ${accent || "bg-[hsl(var(--secondary))]"}`}>
            <Icon className="h-5 w-5 text-[hsl(var(--primary))]" />
          </div>
        )}
      </div>
      <p className="font-heading text-3xl font-bold text-slate-800 mt-2">{value}</p>
    </div>
  );
}

export function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}
