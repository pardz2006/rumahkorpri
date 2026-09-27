import React from "react";
import { Navbar } from "../components/Navbar";
import {
  Users, Building2, FileText, Landmark, ArrowRight, Database, Webhook, MessageSquare, Layout,
} from "lucide-react";

const Section = ({ id, icon: Icon, title, children }) => (
  <section id={id} className="scroll-mt-20">
    <div className="flex items-center gap-3 mb-5">
      <div className="h-10 w-10 rounded-lg bg-[hsl(var(--primary))] grid place-items-center">
        <Icon className="h-5 w-5 text-white" />
      </div>
      <h2 className="font-heading text-2xl font-bold text-slate-800">{title}</h2>
    </div>
    {children}
  </section>
);

const Card = ({ children }) => (
  <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm">{children}</div>
);

const ENDPOINTS = [
  ["POST", "/api/auth/register · /login · GET /me", "Autentikasi JWT untuk 4 peran"],
  ["GET", "/api/projects · /api/projects/{id}", "Daftar proyek & unit (publik)"],
  ["POST", "/api/kpr/simulate", "Kalkulator angsuran (Fix & Floating, FLPP/Komersial)"],
  ["POST", "/api/bookings", "Buat pemesanan unit (consumer)"],
  ["POST", "/api/bookings/{id}/pay", "Inisiasi pembayaran QRIS/VA BTN"],
  ["POST", "/api/payments/webhook", "Webhook verifikasi gateway → generate draft SPR"],
  ["GET", "/api/developer/spr-queue", "Antrean SPR untuk developer"],
  ["POST", "/api/bookings/{id}/spr/approve", "Setujui SPR + tanda tangan → teruskan ke BTN"],
  ["GET", "/api/bookings/{id}/spr.pdf", "Unduh SPR PDF"],
  ["POST", "/api/bookings/{id}/documents", "Unggah dokumen KPR"],
  ["PATCH", "/api/documents/{id}/verify", "Verifikasi dokumen (valid/invalid)"],
  ["POST", "/api/bookings/{id}/followup", "Kirim pengingat WhatsApp otomatis"],
  ["GET", "/api/kpr/applications", "Daftar pengajuan (BTN)"],
  ["PATCH", "/api/kpr/applications/{id}", "Keputusan kelayakan KPR"],
  ["GET", "/api/notifications · /api/wa-logs · /api/stats", "Notifikasi in-app, log WA, statistik"],
];

const COLLECTIONS = [
  ["users", "role (consumer|admin_korpri|admin_developer|btn_evaluator), name, email, password_hash, phone, nik, instansi, monthly_income"],
  ["projects", "name, location, developer_name, program (FLPP|KOMERSIAL), image, description"],
  ["units", "project_id → projects, type, block, number, price, land_area, building_area, status (available|booked|sold)"],
  ["bookings", "user_id, unit_id, project_id, program, dp_percent, tenor_years, kpr_sim, booking_fee, payment_method, payment_status (pending|paid|failed), va_number, spr_status (not_ready|draft|issued), spr_number, spr_pdf, signature"],
  ["kpr_applications", "booking_id, user_id, loan_amount, program, status (pending|pre_approved|approved|rejected|need_revision), slik_note, evaluator_note"],
  ["documents", "booking_id, user_id, doc_type, file_data, status (missing|uploaded|valid|invalid), note"],
  ["notifications", "user_id, title, message, kind, read"],
  ["wa_logs", "booking_id, phone, template, message, status (sent), read"],
];

const WA_TEMPLATES = [
  ["payment_confirmed", "Konfirmasi booking fee diterima setelah webhook pembayaran."],
  ["spr_issued", "SPR terbit — dikirim ke WhatsApp & email peminat."],
  ["doc_reminder", "Pengingat dokumen yang belum lengkap + link upload langsung."],
  ["kpr_status", "Update status kelayakan KPR dari Bank BTN."],
];

export default function Architecture() {
  return (
    <div className="App">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12 space-y-14">
        <header>
          <p className="text-[hsl(var(--accent))] font-semibold text-sm uppercase tracking-wide">Dokumentasi Teknis</p>
          <h1 className="font-heading text-4xl font-bold text-slate-800 mt-2">Arsitektur Sistem Rumah KORPRI</h1>
          <p className="text-slate-500 mt-3">Blueprint lengkap: alur data antar-aktor, skema database, spesifikasi API, template WhatsApp, dan struktur UI.</p>
        </header>

        <Section id="arch" icon={Users} title="1. Alur Data Antar-Aktor">
          <Card>
            <div className="grid sm:grid-cols-4 gap-3 text-center">
              {[
                { i: Users, t: "Peminat / ASN", d: "Isi data, pilih unit, bayar, unggah dokumen" },
                { i: FileText, t: "Admin KORPRI", d: "CRM, checklist dokumen, follow-up WA" },
                { i: Building2, t: "Developer", d: "Setujui SPR, tanda tangan digital" },
                { i: Landmark, t: "Bank BTN", d: "Prakualifikasi & keputusan KPR" },
              ].map((a, i) => (
                <div key={i} className="relative">
                  <div className="bg-[hsl(var(--muted))]/60 rounded-xl p-4">
                    <a.i className="h-6 w-6 text-[hsl(var(--primary))] mx-auto" />
                    <p className="font-semibold text-slate-800 text-sm mt-2">{a.t}</p>
                    <p className="text-xs text-slate-500 mt-1">{a.d}</p>
                  </div>
                  {i < 3 && <ArrowRight className="hidden sm:block absolute top-1/2 -right-2.5 -translate-y-1/2 h-4 w-4 text-slate-300" />}
                </div>
              ))}
            </div>
            <div className="mt-6 text-sm text-slate-600 leading-relaxed bg-slate-50 rounded-lg p-4 font-mono">
              Peminat → [Booking + Bayar] → Gateway Webhook → Draft SPR<br />
              Developer → [Approve + TTD] → SPR Terbit (PDF) → WA + Email<br />
              Sistem → [Forward otomatis] → Bank BTN (KPR Application)<br />
              BTN → [SLIK/Scoring] → Keputusan → Notifikasi Peminat<br />
              KORPRI CRM → [Monitor dokumen] → Follow-Up WA otomatis
            </div>
          </Card>
        </Section>

        <Section id="db" icon={Database} title="2. Skema Database (MongoDB)">
          <div className="space-y-3">
            {COLLECTIONS.map(([name, fields]) => (
              <Card key={name}>
                <p className="font-mono font-semibold text-[hsl(var(--primary))]">{name}</p>
                <p className="text-sm text-slate-600 mt-1 font-mono leading-relaxed">{fields}</p>
              </Card>
            ))}
          </div>
        </Section>

        <Section id="api" icon={Webhook} title="3. Spesifikasi API Endpoint">
          <Card>
            <div className="divide-y divide-slate-100">
              {ENDPOINTS.map(([m, path, desc]) => (
                <div key={path} className="py-2.5 flex flex-wrap items-baseline gap-x-3">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${m === "GET" ? "bg-blue-100 text-blue-700" : m === "POST" ? "bg-emerald-100 text-emerald-700" : "bg-orange-100 text-orange-700"}`}>{m}</span>
                  <code className="text-sm text-slate-700">{path}</code>
                  <span className="text-xs text-slate-400 w-full sm:w-auto sm:ml-auto">{desc}</span>
                </div>
              ))}
            </div>
          </Card>
        </Section>

        <Section id="wa" icon={MessageSquare} title="4. Template Automasi WhatsApp">
          <div className="space-y-3">
            {WA_TEMPLATES.map(([k, d]) => (
              <Card key={k}>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono bg-green-100 text-green-700 px-2 py-0.5 rounded">{k}</span>
                  <p className="text-sm text-slate-600">{d}</p>
                </div>
              </Card>
            ))}
            <Card>
              <p className="text-sm font-mono text-slate-600 whitespace-pre-line leading-relaxed">
{`Halo {nama} 👋
Pengajuan KPR Anda untuk unit {unit} di {proyek} masih menunggu kelengkapan dokumen: {daftar_dokumen}.
Silakan unggah melalui tautan berikut tanpa perlu login rumit:
{link_upload}
Terima kasih 🙏 — CRM Rumah KORPRI`}
              </p>
            </Card>
          </div>
        </Section>

        <Section id="ui" icon={Layout} title="5. Struktur UI/UX">
          <div className="grid sm:grid-cols-2 gap-3">
            <Card>
              <p className="font-semibold text-slate-800">Landing rumahkorpri.com</p>
              <ul className="text-sm text-slate-600 mt-2 space-y-1 list-disc list-inside">
                <li>Hero + CTA pemesanan</li>
                <li>Alur 4 langkah</li>
                <li>Katalog proyek & unit</li>
                <li>Kalkulator simulasi KPR</li>
                <li>Form data & booking</li>
              </ul>
            </Card>
            <Card>
              <p className="font-semibold text-slate-800">Dashboard CRM & Peran</p>
              <ul className="text-sm text-slate-600 mt-2 space-y-1 list-disc list-inside">
                <li>Portal Peminat: bayar, SPR, upload dokumen</li>
                <li>CRM KORPRI: checklist + follow-up WA</li>
                <li>Developer: antrean & TTD SPR</li>
                <li>Bank BTN: penilaian kelayakan KPR</li>
                <li>Notifikasi in-app + log WhatsApp</li>
              </ul>
            </Card>
          </div>
        </Section>
      </div>
    </div>
  );
}
