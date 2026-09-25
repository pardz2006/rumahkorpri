import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Navbar } from "../components/Navbar";
import { api, rupiah, mediaUrl } from "../lib/api";
import { StatusBadge } from "../components/shared";
import { Button } from "../components/ui/button";
import {
  ShieldCheck, FileText, Building2, Landmark, ArrowRight,
  MapPin, CheckCircle2, Wallet, MessagesSquare,
} from "lucide-react";

const HERO = "https://images.pexels.com/photos/3918373/pexels-photo-3918373.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=900&w=1400";

const STEPS = [
  { icon: FileText, t: "Isi Data & Pilih Unit", d: "Lengkapi data ASN, pilih proyek dan unit rumah lewat daftar interaktif." },
  { icon: Wallet, t: "Bayar & Terbitkan SPR", d: "Bayar booking fee via QRIS/VA BTN, SPR otomatis terbit dalam bentuk PDF." },
  { icon: Landmark, t: "Prakualifikasi BTN", d: "Data diteruskan otomatis ke Bank BTN untuk penilaian kelayakan KPR." },
  { icon: MessagesSquare, t: "Follow-Up Dokumen", d: "CRM KORPRI mengingatkan kelengkapan berkas via WhatsApp & in-app." },
];

export default function Landing() {
  const [projects, setProjects] = useState([]);

  useEffect(() => { api.get("/projects").then((r) => setProjects(r.data)).catch(() => {}); }, []);

  return (
    <div className="App">
      <Navbar />

      {/* HERO */}
      <section className="relative grain overflow-hidden">
        <img src={HERO} alt="Perumahan" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 hero-overlay" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-24 sm:py-32">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }} className="max-w-2xl">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/15 border border-white/25 text-white text-sm backdrop-blur-md">
              <ShieldCheck className="h-4 w-4" /> Program Perumahan Khusus ASN & KORPRI
            </span>
            <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight mt-5 leading-[1.05]">
              Wujudkan Rumah Impian Abdi Negara
            </h1>
            <p className="text-lg text-white/85 mt-5 max-w-xl">
              Pesan unit, simulasikan KPR FLPP & Komersial, dan pantau proses pembiayaan Bank BTN dalam satu platform terintegrasi.
            </p>
            <div className="flex flex-wrap gap-3 mt-8">
              <Button asChild size="lg" className="bg-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/90 text-white">
                <a href="#proyek" data-testid="hero-cta-projects">Lihat Proyek Perumahan <ArrowRight className="h-4 w-4 ml-1" /></a>
              </Button>
              <Button asChild size="lg" variant="outline" className="bg-white/10 border-white/30 text-white hover:bg-white/20">
                <a href="#simulasi" data-testid="hero-cta-sim">Simulasi KPR</a>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* WORKFLOW */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
        <div className="text-center max-w-2xl mx-auto">
          <p className="text-[hsl(var(--accent))] font-semibold text-sm uppercase tracking-wide">Alur Pemesanan</p>
          <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-bold text-slate-800 mt-2">Empat Langkah Mudah</h2>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-12">
          {STEPS.map((s, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }} transition={{ delay: i * 0.08 }}
              className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm card-hover">
              <div className="h-11 w-11 rounded-lg bg-[hsl(var(--primary))] grid place-items-center">
                <s.icon className="h-5 w-5 text-white" />
              </div>
              <p className="text-xs font-semibold text-[hsl(var(--accent))] mt-4">LANGKAH {i + 1}</p>
              <p className="font-heading font-semibold text-slate-800 mt-1">{s.t}</p>
              <p className="text-sm text-slate-500 mt-2">{s.d}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* PROJECTS */}
      <section id="proyek" className="bg-[hsl(var(--muted))]/50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-end justify-between mb-10">
            <div>
              <p className="text-[hsl(var(--accent))] font-semibold text-sm uppercase tracking-wide">Proyek Tersedia</p>
              <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-bold text-slate-800 mt-2">Pilih Perumahan Anda</h2>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {projects.map((p) => (
              <Link key={p.id} to={`/proyek/${p.id}`} data-testid={`project-card-${p.id}`}
                className="group bg-white rounded-xl border border-slate-200/80 overflow-hidden shadow-sm card-hover flex flex-col">
                <div className="relative h-52 overflow-hidden">
                  <img src={mediaUrl(p.image)} alt={p.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                  <div className="absolute top-3 left-3 flex gap-1.5">
                    <span className="px-2.5 py-1 rounded-full bg-white/90 text-xs font-semibold text-[hsl(var(--primary))]">
                      {p.program === "FLPP" ? "FLPP Subsidi" : "Komersial"}
                    </span>
                    {p.match_score >= 2 && (
                      <span data-testid={`match-badge-${p.id}`} className="px-2.5 py-1 rounded-full bg-[hsl(var(--accent))] text-xs font-semibold text-white">
                        Dekat domisili Anda
                      </span>
                    )}
                  </div>
                </div>
                <div className="p-5 flex-1 flex flex-col">
                  <h3 className="font-heading text-xl font-semibold text-slate-800">{p.name}</h3>
                  <p className="flex items-center gap-1.5 text-sm text-slate-500 mt-1">
                    <MapPin className="h-4 w-4" /> {p.location}
                  </p>
                  <p className="text-sm text-slate-500 mt-3 line-clamp-2">{p.description}</p>
                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-100">
                    <span className="text-sm text-slate-600">
                      <b className="text-[hsl(var(--primary))]">{p.available_count}</b> dari {p.total_units} unit tersedia
                    </span>
                    <span className="text-sm font-medium text-[hsl(var(--accent))] flex items-center gap-1">
                      Lihat unit <ArrowRight className="h-4 w-4" />
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* SIMULASI TEASER */}
      <section id="simulasi" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
        <div className="bg-[hsl(var(--primary))] rounded-2xl p-8 sm:p-12 grain relative overflow-hidden">
          <div className="relative grid lg:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="font-heading text-2xl sm:text-3xl font-bold text-white">Hitung Angsuran KPR Anda</h2>
              <p className="text-white/80 mt-3">
                Setiap unit dilengkapi kalkulator simulasi interaktif — pilih skema Fix & Floating, tenor 5–30 tahun, dan program FLPP atau Komersial.
              </p>
              <ul className="mt-6 space-y-2">
                {["Estimasi angsuran real-time", "Skema DP fleksibel 0–50%", "Program FLPP bersubsidi 5%"].map((t) => (
                  <li key={t} className="flex items-center gap-2 text-white/90 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-[hsl(var(--secondary))]" /> {t}
                  </li>
                ))}
              </ul>
              <Button asChild size="lg" className="mt-8 bg-white text-[hsl(var(--primary))] hover:bg-white/90">
                <Link to={projects[0] ? `/proyek/${projects[0].id}` : "/"}>Mulai Simulasi <ArrowRight className="h-4 w-4 ml-1" /></Link>
              </Button>
            </div>
            <div className="hidden lg:flex items-center justify-center">
              <Building2 className="h-56 w-56 text-white/10" strokeWidth={1} />
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-200 py-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row justify-between gap-4 text-sm text-slate-500">
          <p>© 2026 rumahkorpri.com — Sistem Pemesanan Rumah & CRM KPR KORPRI</p>
          <div className="flex gap-4">
            <Link to="/arsitektur" className="hover:text-[hsl(var(--primary))]">Dokumentasi Arsitektur</Link>
            <Link to="/login" className="hover:text-[hsl(var(--primary))]">Portal Login</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
