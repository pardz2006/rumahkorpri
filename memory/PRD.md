# PRD — Rumah KORPRI (Sistem Pemesanan Rumah & CRM KPR)

## Problem Statement (Original)
Import project dari GitHub repository: https://github.com/pardz2006/rumahkorpri, branch main. Setup dan install semua dependencies-nya.

## Arsitektur
- Backend: FastAPI + Motor (MongoDB) — /app/backend (server.py, auth.py, db.py, seed.py, kpr.py, spr.py, receipt.py, whatsapp.py, storage.py, geo.py, kpr_pdf.py)
- Frontend: React 19 + CRACO + Tailwind + shadcn/ui — /app/frontend
- DB: MongoDB lokal via MONGO_URL, DB_NAME dari .env

## User Personas
- Peminat/Pembeli (ASN KORPRI)
- Admin/CRM KORPRI
- Mitra Developer
- Bank BTN/DKI Evaluator

## Yang Sudah Diimplementasikan
- 2026-09-27: Import repo GitHub (branch main) ke /app, install dependencies backend (pip) & frontend (yarn), tambah JWT_SECRET di backend/.env, jalankan seed.py (akun admin/developer/bank + data proyek), update memory/test_credentials.md, verifikasi: API health OK, login admin OK, landing page render OK.
- 2026-09-27: Peningkatan ZoomableImage — lightbox kini memakai container scroll native (scrollbar horizontal & vertikal muncul saat zoom), geser via scrollbar/drag mouse/sentuhan, zoom via tombol/scroll/klik 2x/cubit dengan anchor kursor, thumbnail layout/siteplan/peta object-contain agar tidak terpotong.
- 2026-09-27: Logo Rumah KORPRI resmi (https://www.rumahkorpri.com/logo_rumah_korpri.png) dipasang di Navbar, halaman Login, dan PublicSimulation menggantikan ikon generik; URL diekspor sebagai LOGO_URL di lib/api.js.

## Catatan Teknis
- requirements.txt: baris `litellm @ <url>#sha256=...` konflik dengan dependensi emergentintegrations saat resolve; install dilakukan dengan filter baris tersebut (litellm tetap terpasang via emergentintegrations).
- EMERGENT_LLM_KEY / TWILIO_* opsional (dipakai storage.py/whatsapp.py bila tersedia).

## Backlog / Next Tasks
- P0: Verifikasi flow end-to-end (booking, SPR PDF, dashboard admin/developer/bank) bila diminta.
- P1: Tambahkan EMERGENT_LLM_KEY ke backend/.env bila fitur storage/LLM dipakai.
- P2: Konfigurasi Twilio WhatsApp bila notifikasi WA asli diperlukan.
